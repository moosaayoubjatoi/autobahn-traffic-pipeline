# Fuel Price Pipeline (Ostwestfalen-Lippe)

A small batch data pipeline that collects fuel prices (diesel, E5, E10) from petrol stations in
Lemgo, Detmold, Bielefeld and Paderborn and stores them for analysis.

**Status:** work in progress. Step 1 (extract + load) is done.

## How it works

```
Tankerkönig API ──► extract.py ──► data/raw/*.json ──► load.py ──► DuckDB (raw_stations, raw_prices)
                                                                      │
                                                         dbt models (planned) ──► dashboard (planned)
```

| Step | What it does | Tools |
|---|---|---|
| Extract | Calls the API for 4 cities (5 km radius each) and saves the response unchanged | Python, requests |
| Load | Reads all raw files into DuckDB; files already loaded are skipped (idempotent) | DuckDB, SQL |
| Test | Unit tests with a fake API response, no internet needed | pytest |

## Run it

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m pipeline.extract    # fetch prices
python -m pipeline.load       # load into data/fuel_prices.duckdb
python -m pytest              # run tests
```

Without an API key the public demo key is used: station data is real, prices are placeholders.
For real prices, get a free key at <https://creativecommons.tankerkoenig.de> and set
`TANKERKOENIG_API_KEY` as an environment variable.

## Roadmap

- [x] Extract raw JSON from the API
- [x] Idempotent load into DuckDB
- [ ] dbt models: staging, cleaned prices, daily price per city and brand, data quality tests
- [ ] Scheduled runs with GitHub Actions
- [ ] Streamlit dashboard: cheapest time of day, brand comparison

## Data source

Fuel price data: [Tankerkönig](https://creativecommons.tankerkoenig.de), based on MTS-K data,
licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
