"""Extract: fetch current fuel prices from the Tankerkönig API and save the raw JSON.

One file per run and city: data/raw/YYYY-MM-DD/<city>_<HHMMSS>.json
Raw data is saved unchanged, so it can always be reloaded if the SQL logic changes.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://creativecommons.tankerkoenig.de/json/list.php"

# Public demo key from the Tankerkönig docs: real stations, fake prices.
DEMO_KEY = "00000000-0000-0000-0000-000000000002"

# Cities in Ostwestfalen-Lippe (lat, lng). Radius in km (API maximum is 25).
LOCATIONS = {
    "lemgo": (52.028, 8.900),
    "detmold": (51.938, 8.879),
    "bielefeld": (52.021, 8.532),
    "paderborn": (51.719, 8.754),
}
RADIUS_KM = 5

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def get_api_key() -> str:
    """Read the key from the environment; fall back to the demo key."""
    return os.environ.get("TANKERKOENIG_API_KEY", DEMO_KEY)


def fetch_stations(lat: float, lng: float, api_key: str) -> dict:
    """Call the API once and return the parsed JSON. Raises on HTTP or API errors."""
    params = {
        "lat": lat,
        "lng": lng,
        "rad": RADIUS_KM,
        "sort": "dist",
        "type": "all",
        "apikey": api_key,
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"API error: {payload.get('message')}")
    return payload


def save_raw(payload: dict, city: str, fetched_at: datetime, raw_dir: Path = RAW_DIR) -> Path:
    """Write the API response plus metadata (city, time, demo flag) to a JSON file."""
    day_dir = raw_dir / fetched_at.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{city}_{fetched_at.strftime('%H%M%S')}.json"
    record = {
        "city": city,
        "fetched_at": fetched_at.isoformat(),
        "is_demo": get_api_key() == DEMO_KEY,
        "response": payload,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run() -> list[Path]:
    api_key = get_api_key()
    if api_key == DEMO_KEY:
        print("Using the demo key: prices are not real. Set TANKERKOENIG_API_KEY for real data.")
    fetched_at = datetime.now(timezone.utc)
    paths = []
    for city, (lat, lng) in LOCATIONS.items():
        payload = fetch_stations(lat, lng, api_key)
        path = save_raw(payload, city, fetched_at)
        print(f"{city}: {len(payload['stations'])} stations -> {path.name}")
        paths.append(path)
    return paths


if __name__ == "__main__":
    run()
