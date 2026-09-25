# Workflow / Data Model Diagram

This renders automatically on GitHub (Mermaid support built in).

## Entity / event model

```mermaid
erDiagram
    ZONE {
        int LocationID
        string Borough
        string Zone
        string service_zone
    }
    TRIP {
        int trip_id
        datetime pickup_datetime
        datetime dropoff_datetime
        int PULocationID
        int DOLocationID
        float trip_distance
        float fare_amount
        int passenger_count
        bool is_flagged
    }
    WEATHER {
        date date
        float precipitation_mm
        float temp_avg_c
    }

    ZONE ||--o{ TRIP : "pickup zone"
    ZONE ||--o{ TRIP : "dropoff zone"
    WEATHER ||--o{ TRIP : "happened on"
```

## Pipeline flow

```mermaid
flowchart LR
    A[Raw trip CSV] --> D[Ingest]
    B[Zone lookup CSV] --> D
    C[Weather API / cached JSON] --> D
    D --> E[Validate: profile + flag bad rows]
    E --> F[Model: join zones + weather, derive duration/speed]
    F --> G[Metrics: 5 KPI-linked metrics]
    G --> H[(metrics_output.csv / .json)]
    E --> I[(flagged_records.csv)]
```

## Notes

- `TRIP` is the event table — one row per trip.
- `ZONE` is joined twice (once for pickup, once for dropoff) since a trip
  has two locations.
- `WEATHER` is joined by date only (daily granularity), not by exact
  pickup time — documented as a limitation in the README.
- Flagged trips are NOT deleted; they flow into `flagged_records.csv`
  separately so nothing is silently dropped.
