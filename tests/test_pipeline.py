"""Tests run without internet: they use a small fake API response."""

from datetime import datetime, timezone

import duckdb

from pipeline import extract, load

FAKE_WARNINGS = {
    "warning": [
        {"identifier": "w1", "display_type": "WARNING", "title": "A2 | Bielefeld-Ost - Herford ",
         "subtitle": " Dortmund -> Hannover", "isBlocked": "false", "future": False,
         "coordinate": {"lat": "52.05", "long": "8.62"}, "startTimestamp": "2026-11-13T07:30:00Z",
         "delayTimeValue": "15", "abnormalTrafficType": "SLOW_TRAFFIC",
         "description": ["Beginn: 13.11.26 um 08:30 Uhr", "Stockender Verkehr"]},
        {"identifier": "w2", "display_type": "WARNING", "title": "A2 | Rehren - Bad Eilsen",
         "isBlocked": "true", "coordinate": {}, "description": []},
    ]
}


def make_raw_file(tmp_path):
    fetched_at = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
    return extract.save_raw(FAKE_WARNINGS, "A2", "warning", fetched_at, raw_dir=tmp_path)


def test_save_raw_writes_dated_file(tmp_path):
    path = make_raw_file(tmp_path)
    assert path.parent.name == "2026-11-13"
    assert path.name == "A2_warning_120000.json"


def test_to_bool_handles_strings_and_booleans():
    assert load.to_bool("true") is True
    assert load.to_bool("false") is False
    assert load.to_bool(True) is True
    assert load.to_bool(None) is None


def test_parse_event_cleans_fields():
    row = load.parse_event(FAKE_WARNINGS["warning"][0])
    assert row["title"] == "A2 | Bielefeld-Ost - Herford"
    assert row["delay_minutes"] == 15
    assert row["lat"] == 52.05
    assert row["description"] == "Beginn: 13.11.26 um 08:30 Uhr\nStockender Verkehr"

    sparse = load.parse_event(FAKE_WARNINGS["warning"][1])
    assert sparse["lat"] is None
    assert sparse["delay_minutes"] is None
    assert sparse["is_blocked"] is True


def test_load_is_idempotent(tmp_path):
    make_raw_file(tmp_path)
    db = tmp_path / "test.duckdb"

    assert load.run(db_path=db, raw_dir=tmp_path) == 2
    assert load.run(db_path=db, raw_dir=tmp_path) == 0  # second run loads nothing

    con = duckdb.connect(str(db))
    assert con.execute("SELECT count(*) FROM raw_events").fetchone()[0] == 2
    con.close()
