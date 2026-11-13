"""Tests run without internet: they use a small fake API response."""

from datetime import datetime, timezone

import duckdb

from pipeline import extract, load

FAKE_RESPONSE = {
    "ok": True,
    "status": "ok",
    "stations": [
        {"id": "a1", "name": "Station A", "brand": "Shell", "street": "Bruchweg", "houseNumber": "48",
         "postCode": 32657, "place": "Lemgo", "lat": 52.03, "lng": 8.90,
         "diesel": 1.659, "e5": 1.799, "e10": 1.739, "isOpen": True},
        {"id": "b2", "name": "Station B", "brand": "ARAL", "street": "Hauptstr.", "houseNumber": "1",
         "postCode": 32657, "place": "Lemgo", "lat": 52.02, "lng": 8.91,
         "diesel": False, "e5": 1.819, "e10": None, "isOpen": False},
    ],
}


def make_raw_file(tmp_path, city="lemgo"):
    fetched_at = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
    return extract.save_raw(FAKE_RESPONSE, city, fetched_at, raw_dir=tmp_path)


def test_save_raw_writes_dated_file(tmp_path):
    path = make_raw_file(tmp_path)
    assert path.parent.name == "2026-11-13"
    assert path.name == "lemgo_120000.json"


def test_to_price_turns_false_and_none_into_null():
    assert load.to_price(1.659) == 1.659
    assert load.to_price(False) is None
    assert load.to_price(None) is None


def test_load_is_idempotent(tmp_path):
    make_raw_file(tmp_path)
    db = tmp_path / "test.duckdb"

    assert load.run(db_path=db, raw_dir=tmp_path) == 2
    assert load.run(db_path=db, raw_dir=tmp_path) == 0  # second run loads nothing

    con = duckdb.connect(str(db))
    assert con.execute("SELECT count(*) FROM raw_prices").fetchone()[0] == 2
    diesel_b2 = con.execute("SELECT diesel FROM raw_prices WHERE station_id = 'b2'").fetchone()[0]
    assert diesel_b2 is None
    con.close()
