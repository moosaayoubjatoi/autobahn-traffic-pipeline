# Autobahn Traffic Pipeline (Ostwestfalen-Lippe)

A batch data pipeline that collects roadworks, traffic warnings and closures on the autobahns
around Ostwestfalen-Lippe (A2, A30, A33, A44) and stores every snapshot for analysis.

Questions it will answer: Which stretches are closed most often? How long do roadworks last?
When do traffic jams happen and how long are the delays?

**Status:** work in progress. Step 1 (extract + load) is done.

## How it works

```
Autobahn API ──► extract.py ──► data/raw/*.json ──► load.py ──► DuckDB (raw_events)
                                                                   │
                                                      dbt models (planned) ──► dashboard (planned)
```

| Step | What it does | Tools |
|---|---|---|
| Extract | Calls the API for 4 roads × 3 event types and saves each response unchanged | Python, requests |
| Load | Reads all raw files into DuckDB, one row per event per run; files already loaded are skipped (idempotent) | DuckDB, SQL |
| Test | Unit tests with a fake API response, no internet needed | pytest |

Each run is a snapshot. Running the pipeline repeatedly shows when an event first appeared
and when it disappeared, which gives its duration.

## Run it

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m pipeline.extract    # fetch current events
python -m pipeline.load       # load into data/autobahn.duckdb
python -m pytest              # run tests
```

No API key or registration needed.

## Roadmap

- [x] Extract raw JSON from the API
- [x] Idempotent load into DuckDB
- [ ] dbt models: staging, OWL region filter, one row per event with first/last seen, data quality tests
- [ ] Scheduled runs with GitHub Actions
- [ ] Streamlit dashboard: closures per stretch, roadworks duration, delays by hour

## Data source

[Autobahn GmbH des Bundes](https://verkehr.autobahn.de/o/autobahn) public traffic API.
