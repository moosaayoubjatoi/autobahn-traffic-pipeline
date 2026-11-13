"""Load: read all raw JSON files into a DuckDB table.

raw_events : one row per event per fetch (a snapshot). Because the pipeline runs
             repeatedly, the snapshots show when an event first appeared and when it ended.

Loading is idempotent: a file that is already loaded is skipped,
so the script can run again and again without creating duplicates.
"""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "autobahn.duckdb"

SCHEMA = """
CREATE TABLE IF NOT EXISTS loaded_files (
    file_name  VARCHAR PRIMARY KEY,
    loaded_at  TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS raw_events (
    event_id         VARCHAR,
    fetched_at       TIMESTAMPTZ,
    road             VARCHAR,
    event_type       VARCHAR,     -- roadworks | warning | closure
    display_type     VARCHAR,     -- e.g. SHORT_TERM_ROADWORKS, WARNING, CLOSURE
    title            VARCHAR,
    subtitle         VARCHAR,     -- direction, e.g. "Dortmund -> Hannover"
    is_blocked       BOOLEAN,
    is_future        BOOLEAN,
    lat              DOUBLE,
    lng              DOUBLE,
    start_timestamp  TIMESTAMPTZ, -- only warnings have this
    delay_minutes    INTEGER,     -- only warnings have this
    traffic_type     VARCHAR,     -- e.g. SLOW_TRAFFIC, STATIONARY_TRAFFIC
    description      VARCHAR,
    source_file      VARCHAR,
    PRIMARY KEY (event_id, fetched_at)
);
"""


def to_bool(value):
    """The API sends booleans sometimes as true/false, sometimes as the strings "true"/"false"."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return None


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_event(e: dict) -> dict:
    """Pick and clean the fields we keep from one API event."""
    coordinate = e.get("coordinate") or {}
    return {
        "event_id": e["identifier"],
        "display_type": e.get("display_type"),
        "title": (e.get("title") or "").strip(),
        "subtitle": (e.get("subtitle") or "").strip(),
        "is_blocked": to_bool(e.get("isBlocked")),
        "is_future": to_bool(e.get("future")),
        "lat": float(coordinate["lat"]) if "lat" in coordinate else None,
        "lng": float(coordinate["long"]) if "long" in coordinate else None,
        "start_timestamp": e.get("startTimestamp"),
        "delay_minutes": to_int(e.get("delayTimeValue")),
        "traffic_type": e.get("abnormalTrafficType"),
        "description": "\n".join(e.get("description") or []),
    }


def load_file(con: duckdb.DuckDBPyConnection, path: Path, raw_dir: Path = RAW_DIR) -> int:
    """Load one raw file. Returns the number of rows inserted (0 if already loaded)."""
    file_name = path.relative_to(raw_dir).as_posix()
    if con.execute("SELECT 1 FROM loaded_files WHERE file_name = ?", [file_name]).fetchone():
        return 0

    record = json.loads(path.read_text(encoding="utf-8"))
    events = record["response"].get(record["event_type"], [])

    for e in events:
        row = parse_event(e)
        con.execute(
            """
            INSERT INTO raw_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [row["event_id"], record["fetched_at"], record["road"], record["event_type"],
             row["display_type"], row["title"], row["subtitle"], row["is_blocked"],
             row["is_future"], row["lat"], row["lng"], row["start_timestamp"],
             row["delay_minutes"], row["traffic_type"], row["description"], file_name],
        )

    con.execute("INSERT INTO loaded_files (file_name) VALUES (?)", [file_name])
    return len(events)


def run(db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> int:
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA)
    total = 0
    for path in sorted(raw_dir.glob("*/*.json")):
        total += load_file(con, path, raw_dir)
    rows = con.execute("SELECT count(*) FROM raw_events").fetchone()[0]
    con.close()
    print(f"Loaded {total} new rows. Database now holds {rows} event snapshots.")
    return total


if __name__ == "__main__":
    run()
