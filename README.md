# NYC Taxi Trip Reliability Pipeline

A small FDE-style project: take raw NYC TLC-style taxi trip data, validate it,
model it as a workflow, and produce a repeatable set of operational metrics.

## Problem

NYC Taxi & Limousine Commission (TLC) publishes millions of trip records every
month across multiple files (trip records, zone lookup tables). On their own,
these files are just event logs — they don't answer operational questions
like "how efficient are trips in each borough?" or "does trip duration behave
differently in the rain?" This project turns raw trip + zone + weather data
into a small, trustworthy, repeatable metrics pipeline that could support
real dispatch/planning decisions.

## Users / stakeholders

- **Taxi dispatch / fleet planning team** — wants to know where and when
  trips are slow or inefficient, to plan vehicle allocation.
- **Data/analytics team** — needs the underlying data validated and
  documented before trusting it for reporting.
- **Ops leadership** — wants a small number of reliable KPIs, not a raw
  data dump.

## Project KPI

**Trip Duration & Efficiency Reliability** — can we trust how long a trip
takes and what it costs, broken down by borough and by weather condition?
This is the anchor KPI; all 5 metrics below are linked to it.

## Source overview (source map)

| Source | What it provides | Retrieval mode | Owner (in real life) |
|---|---|---|---|
| `trips_march2024_sample.csv` | Trip-level events: pickup/dropoff time, location IDs, distance, fare, passengers | File (CSV) | TLC trip records |
| `taxi_zone_lookup.csv` | Reference table mapping LocationID → Borough/Zone | File (CSV) | TLC zone lookup |
| Weather (Open-Meteo API, cached fallback included) | Daily precipitation + temperature for NYC | API (with cached JSON fallback) | Open-Meteo (external) |

**Note on data used here:** This sandbox environment cannot reach external
sites (nyc.gov, open-meteo.com), so `src/generate_sample_data.py` generates a
**synthetic sample** that copies the real TLC schema exactly (same column
names/types) and a cached weather API response shaped like a real Open-Meteo
response. The pipeline code itself (`ingest.py`) contains the real,
working API call — it just falls back to the cached file if the live call
fails, which is what happened when I ran it here (see `logs/pipeline.log`).

**To use real data instead:** download the real files and drop them into
`data/raw/` with the same filenames used in `src/ingest.py`:
- Trip data: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- Zone lookup: https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
- Weather API: https://open-meteo.com/en/docs (no API key required)

## Workflow / data model

See `diagrams/workflow_diagram.md` for the entity/event diagram.

Short version: **Trip** is the core event (pickup → dropoff). Each trip is
enriched by joining to the **Zone** entity (pickup + dropoff borough/zone)
and to **Weather** context data (by date). Validation flags are attached to
each trip rather than silently dropping bad rows.

## Metrics produced (evidence table)

1. Average trip duration (minutes) by pickup borough
2. Average speed (mph) overall and by borough
3. Trip volume by hour of day (demand pattern)
4. Average fare per mile on rainy vs. non-rainy days
5. % of records flagged as invalid (data quality metric)

Output: `data/processed/metrics_output.csv` and `.json`

## Known / Unknown / Assumption / Limitation

**Known**
- The pipeline runs end-to-end and is rerun-safe (output files are
  overwritten, not appended, on each run).
- ~2.7% of sample trip records were flagged as invalid by the validation
  rules (see `data/processed/flagged_records.csv`).

**Unknown**
- Whether the real TLC data has the same proportion of bad records as this
  synthetic sample — the real proportion could be higher or lower.

**Assumptions**
- A trip is only "invalid" if it fails one of five explicit rules (see
  `src/validate.py` docstring) — anything not caught by those rules is
  treated as valid, even if it looks unusual.
- "Rainy day" = more than 1mm of precipitation that day (a simplification;
  real dispatch decisions might use hourly rain, not daily totals).
- Zone lookup in this sample is a simplified 20-zone list, not the real
  265-zone TLC table, to keep the project easy to reason about at a
  student level.

**Limitations**
- Only one month of data is used; seasonal patterns aren't captured.
- Weather is joined at day-level only, not matched to the exact pickup
  hour.
- Live weather API access was not available in the environment this was
  built in, so the demo run used the cached fallback response — this is
  logged, not hidden (see `logs/pipeline.log`).

## Setup & run instructions

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) regenerate the sample raw data
python src/generate_sample_data.py

# 3. Run the full pipeline (ingest -> validate -> model -> metrics)
python src/pipeline.py

# 4. Check outputs
cat data/processed/metrics_output.csv
cat logs/pipeline.log
```

## What decision this output supports

The dispatch/planning team can use the borough-level speed and duration
metrics to see where trips are systematically slower (candidate areas for
more vehicles or different routing), and the rainy-vs-non-rainy fare/mile
comparison to evaluate whether pricing or supply should adjust on wet days.
The data-quality metric (% flagged) tells the analytics team how much they
can trust a given month's data before using it in a report.

## Project structure

```
fde-nyc-taxi-pipeline/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/            # source inputs (never modified by the pipeline)
│   └── processed/      # pipeline outputs (overwritten each run)
├── src/
│   ├── generate_sample_data.py   # NOT part of the pipeline; creates demo data
│   ├── ingest.py        # Class 5: retrieval (file + API)
│   ├── validate.py      # Class 6: profiling + validation rules
│   ├── model.py          # Class 7: workflow/entity model
│   ├── metrics.py        # Class 7: KPI-linked metrics
│   └── pipeline.py       # Class 8: orchestration, logging, failure handling
├── diagrams/
│   └── workflow_diagram.md
└── logs/
    └── pipeline.log      # generated on run
```
