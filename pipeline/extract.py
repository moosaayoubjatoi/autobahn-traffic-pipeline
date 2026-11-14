"""Extract: fetch roadworks, warnings and closures from the Autobahn API and save the raw JSON.

API: https://verkehr.autobahn.de/o/autobahn (Autobahn GmbH des Bundes, no API key needed)
One file per run, road and event type: data/raw/YYYY-MM-DD/<road>_<type>_<HHMMSS>.json
Raw data is saved unchanged, so it can always be reloaded if the SQL logic changes.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://verkehr.autobahn.de/o/autobahn/{road}/services/{event_type}"

# Autobahns that run through Ostwestfalen-Lippe. The API returns the whole road;
# the OWL filter happens later in SQL.
ROADS = ["A2", "A30", "A33", "A44"]
EVENT_TYPES = ["roadworks", "warning", "closure"]

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def make_session() -> requests.Session:
    """HTTP session that retries temporary server errors (e.g. a 502 from the API proxy).

    Up to 4 retries with waits of 2, 4, 8, 16 s. A road/type that still fails after that
    stops the run on purpose: skipping it would make its events look finished in fct_events.
    """
    retry = Retry(total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


SESSION = make_session()


def fetch_events(road: str, event_type: str) -> dict:
    """Call the API (with retries) and return the parsed JSON. Raises on HTTP errors."""
    response = SESSION.get(API_URL.format(road=road, event_type=event_type), timeout=30)
    response.raise_for_status()
    return response.json()


def save_raw(payload: dict, road: str, event_type: str, fetched_at: datetime,
             raw_dir: Path = RAW_DIR) -> Path:
    """Write the API response plus metadata (road, type, time) to a JSON file."""
    day_dir = raw_dir / fetched_at.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{road}_{event_type}_{fetched_at.strftime('%H%M%S')}.json"
    record = {
        "road": road,
        "event_type": event_type,
        "fetched_at": fetched_at.isoformat(),
        "response": payload,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run() -> list[Path]:
    fetched_at = datetime.now(timezone.utc)
    paths = []
    for road in ROADS:
        for event_type in EVENT_TYPES:
            payload = fetch_events(road, event_type)
            path = save_raw(payload, road, event_type, fetched_at)
            print(f"{road} {event_type}: {len(payload.get(event_type, []))} events -> {path.name}")
            paths.append(path)
    return paths


if __name__ == "__main__":
    run()
