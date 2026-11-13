"""Streamlit dashboard for the Autobahn Traffic Pipeline.

Reads the dbt tables from data/autobahn.duckdb (read-only).
Run: streamlit run dashboard/app.py
"""

import tempfile
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import requests
import streamlit as st

LOCAL_DB = Path(__file__).resolve().parent.parent / "data" / "autobahn.duckdb"
# Online (Streamlit Cloud) there is no local database: download the one that
# GitHub Actions keeps on the "data" branch.
DATA_URL = "https://raw.githubusercontent.com/moosaayoubjatoi/autobahn-traffic-pipeline/data/autobahn.duckdb"


@st.cache_resource(ttl=600)
def get_db_path() -> Path | None:
    if LOCAL_DB.exists():
        return LOCAL_DB
    try:
        response = requests.get(DATA_URL, timeout=60)
        response.raise_for_status()
    except requests.RequestException:
        return None
    path = Path(tempfile.gettempdir()) / "autobahn.duckdb"
    path.write_bytes(response.content)
    return path


DB_PATH = get_db_path()

# One fixed colour per event type (validated colour-blind-safe set), so a type keeps
# its colour whatever the filters show.
TYPE_LABELS = {"roadworks": "Roadworks", "closure": "Closure", "warning": "Traffic warning"}
TYPE_COLORS = {"Roadworks": "#2a78d6", "Closure": "#eb6834", "Traffic warning": "#1baf7a"}
COLOR_SCALE = alt.Scale(domain=list(TYPE_COLORS), range=list(TYPE_COLORS.values()))

st.set_page_config(page_title="Autobahn traffic in OWL", layout="wide")


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(sql).df()


if DB_PATH is None:
    st.error("No data yet. Locally: run `python -m pipeline.run`. Online: wait for the first scheduled run.")
    st.stop()

events = query("select * from fct_events")
events["type"] = events["event_type"].map(TYPE_LABELS)
runs = query("""
    select fetched_at, event_type, count(*) as events
    from stg_events where is_in_owl
    group by all order by fetched_at
""")
runs["type"] = runs["event_type"].map(TYPE_LABELS)
last_run = runs["fetched_at"].max()
run_count = runs["fetched_at"].nunique()

# ---------- Header ----------
st.title("Autobahn traffic in Ostwestfalen-Lippe")
st.caption(
    f"A2, A30, A33, A44 · last update {last_run:%d.%m.%Y %H:%M} UTC · {run_count} pipeline run(s) · "
    "Source: Autobahn GmbH des Bundes"
)

# ---------- Filters (one row) ----------
f1, f2, f3 = st.columns([2, 3, 2])
roads = f1.multiselect("Road", sorted(events["road"].unique()), default=sorted(events["road"].unique()))
types = f2.multiselect("Event type", list(TYPE_COLORS), default=list(TYPE_COLORS))
only_active = f3.toggle("Only active now", value=True)

view = events[events["road"].isin(roads) & events["type"].isin(types)]
if only_active:
    view = view[view["is_active"]]

# ---------- KPIs ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Roadworks", int((view["type"] == "Roadworks").sum()))
k2.metric("Closures", int((view["type"] == "Closure").sum()))
k3.metric("Traffic warnings", int((view["type"] == "Traffic warning").sum()))
worst = view["max_delay_minutes"].max()
k4.metric("Worst delay", f"{int(worst)} min" if pd.notna(worst) else "none")

if view.empty:
    st.info("No events match these filters.")
    st.stop()

# ---------- Map + top stretches ----------
left, right = st.columns([1, 1])

with left:
    st.subheader("Where")
    map_df = view.dropna(subset=["lat", "lng"]).assign(color=lambda d: d["type"].map(TYPE_COLORS))
    st.map(map_df, latitude="lat", longitude="lng", color="color", size=250)
    st.caption("Blue: roadworks · Orange: closure · Green: traffic warning")

with right:
    st.subheader("Stretches with the most events")
    top = (
        view.groupby(["road", "stretch", "type"]).size().reset_index(name="events")
        .assign(label=lambda d: d["road"] + " · " + d["stretch"].str.slice(0, 45))
    )
    order = top.groupby("label")["events"].sum().sort_values(ascending=False).head(10).index.tolist()
    top = top[top["label"].isin(order)]
    chart = (
        alt.Chart(top)
        .mark_bar(cornerRadiusEnd=4, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("sum(events):Q", title="Events", axis=alt.Axis(tickMinStep=1, grid=True)),
            y=alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=320)),
            color=alt.Color("type:N", scale=COLOR_SCALE, legend=alt.Legend(title=None, orient="top")),
            tooltip=[alt.Tooltip("road:N", title="Road"), alt.Tooltip("stretch:N", title="Stretch"),
                     alt.Tooltip("type:N", title="Type"), alt.Tooltip("sum(events):Q", title="Events")],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, width="stretch")

# ---------- Over time ----------
st.subheader("Active events per pipeline run")
if run_count < 2:
    st.info("Only one pipeline run so far. This chart fills in once the pipeline runs on a schedule.")
else:
    runs_view = runs[runs["type"].isin(types)]
    line = (
        alt.Chart(runs_view)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=64))
        .encode(
            x=alt.X("fetched_at:T", title=None, axis=alt.Axis(format="%d.%m %H:%M", tickCount=6, labelAngle=0)),
            y=alt.Y("events:Q", title="Active events"),
            color=alt.Color("type:N", scale=COLOR_SCALE, legend=alt.Legend(title=None, orient="top")),
            tooltip=[alt.Tooltip("fetched_at:T", title="Run", format="%d.%m %H:%M"),
                     alt.Tooltip("type:N", title="Type"), alt.Tooltip("events:Q", title="Events")],
        )
        .properties(height=280)
    )
    st.altair_chart(line, width="stretch")

# ---------- Table ----------
st.subheader("All events")
st.dataframe(
    view.sort_values(["road", "type", "stretch"])[
        ["road", "type", "stretch", "direction", "first_seen_at", "last_seen_at", "max_delay_minutes", "was_blocked"]
    ],
    hide_index=True,
    width="stretch",
    column_config={
        "road": "Road", "type": "Type", "stretch": "Stretch", "direction": "Direction / junction",
        "first_seen_at": st.column_config.DatetimeColumn("First seen", format="DD.MM.YY HH:mm"),
        "last_seen_at": st.column_config.DatetimeColumn("Last seen", format="DD.MM.YY HH:mm"),
        "max_delay_minutes": "Max delay (min)", "was_blocked": "Blocked",
    },
)
st.caption("OWL area is approximate (two lat/lng boxes); places just over the border can appear.")
