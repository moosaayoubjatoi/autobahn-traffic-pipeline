"""Load: read all raw JSON files into DuckDB tables.

raw_stations : one row per station (latest known address and location)
raw_prices   : one row per station per fetch (diesel, e5, e10 prices)

Loading is idempotent: a file that is already loaded is skipped,
so the script can run again and again without creating duplicates.
"""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "fuel_prices.duckdb"

SCHEMA = """
CREATE TABLE IF NOT EXISTS loaded_files (
    file_name  VARCHAR PRIMARY KEY,
    loaded_at  TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS raw_stations (
    station_id   VARCHAR PRIMARY KEY,
    name         VARCHAR,
    brand        VARCHAR,
    street       VARCHAR,
    house_number VARCHAR,
    post_code    VARCHAR,
    place        VARCHAR,
    lat          DOUBLE,
    lng          DOUBLE,
    city_query   VARCHAR
);

CREATE TABLE IF NOT EXISTS raw_prices (
    station_id  VARCHAR,
    fetched_at  TIMESTAMPTZ,
    is_open     BOOLEAN,
    diesel      DOUBLE,
    e5          DOUBLE,
    e10         DOUBLE,
    is_demo     BOOLEAN,
    source_file VARCHAR,
    PRIMARY KEY (station_id, fetched_at)
);
"""


def to_price(value):
    """The API returns false or null when a fuel type is not sold. Store that as NULL."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def load_file(con: duckdb.DuckDBPyConnection, path: Path, raw_dir: Path = RAW_DIR) -> int:
    """Load one raw file. Returns the number of price rows inserted (0 if already loaded)."""
    file_name = path.relative_to(raw_dir).as_posix()
    if con.execute("SELECT 1 FROM loaded_files WHERE file_name = ?", [file_name]).fetchone():
        return 0

    record = json.loads(path.read_text(encoding="utf-8"))
    stations = record["response"]["stations"]

    for s in stations:
        con.execute(
            """
            INSERT OR REPLACE INTO raw_stations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [s["id"], s.get("name"), s.get("brand"), s.get("street"), s.get("houseNumber"),
             str(s.get("postCode") or ""), s.get("place"), s.get("lat"), s.get("lng"), record["city"]],
        )
        # The same station can appear in two city searches in the same run: keep the first.
        con.execute(
            """
            INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [s["id"], record["fetched_at"], s.get("isOpen"), to_price(s.get("diesel")),
             to_price(s.get("e5")), to_price(s.get("e10")), record["is_demo"], file_name],
        )

    con.execute("INSERT INTO loaded_files (file_name) VALUES (?)", [file_name])
    return len(stations)


def run(db_path: Path = DB_PATH, raw_dir: Path = RAW_DIR) -> int:
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA)
    total = 0
    for path in sorted(raw_dir.glob("*/*.json")):
        total += load_file(con, path, raw_dir)
    stations = con.execute("SELECT count(*) FROM raw_stations").fetchone()[0]
    prices = con.execute("SELECT count(*) FROM raw_prices").fetchone()[0]
    con.close()
    print(f"Loaded {total} new rows. Database now holds {stations} stations, {prices} price rows.")
    return total


if __name__ == "__main__":
    run()
