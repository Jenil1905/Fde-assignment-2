"""
generate_sample_data.py

This script is NOT part of the real pipeline. It only exists to create sample
input files so the pipeline can be run and demoed without needing to download
the real NYC TLC files (which are large and require internet access).

For the real submission, replace these files with actual downloads:
- Trip data (Yellow Taxi, Parquet/CSV):
  https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- Taxi zone lookup table (CSV):
  https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
- Weather (free, no API key needed):
  https://open-meteo.com/en/docs (historical weather API)

The synthetic data below copies the REAL column names/types used by TLC so
the rest of the pipeline (ingest/validate/model/metrics) works unchanged on
real data too.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

np.random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Trip data (mimics real TLC yellow taxi trip record columns)
# ---------------------------------------------------------------------------
N = 3000  # small sample, enough to demo validation + metrics

# a simplified zone list (real file has 265 zones across 5 boroughs; we use
# a representative subset for a learning project)
boroughs = {
    "Manhattan": list(range(1, 6)),
    "Brooklyn": list(range(6, 11)),
    "Queens": list(range(11, 16)),
    "Bronx": list(range(16, 19)),
    "Staten Island": [19, 20],
}
all_zone_ids = [z for zones in boroughs.values() for z in zones]

start_date = datetime(2024, 3, 1)

rows = []
for i in range(N):
    pickup_offset_min = np.random.randint(0, 31 * 24 * 60)  # spread over March 2024
    pickup_dt = start_date + timedelta(minutes=int(pickup_offset_min))
    trip_minutes = max(1, np.random.gamma(shape=2.0, scale=9.0))  # realistic skew
    dropoff_dt = pickup_dt + timedelta(minutes=trip_minutes)

    distance = max(0.1, np.random.gamma(shape=2.0, scale=1.6))
    fare = round(3.0 + distance * np.random.uniform(2.2, 3.2), 2)
    passengers = np.random.choice([1, 1, 1, 2, 2, 3, 4], p=[0.4,0.15,0.15,0.15,0.05,0.05,0.05])

    pu_id = int(np.random.choice(all_zone_ids))
    do_id = int(np.random.choice(all_zone_ids))

    rows.append({
        "trip_id": i + 1,
        "tpep_pickup_datetime": pickup_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "tpep_dropoff_datetime": dropoff_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "PULocationID": pu_id,
        "DOLocationID": do_id,
        "trip_distance": round(distance, 2),
        "fare_amount": fare,
        "passenger_count": passengers,
        "payment_type": int(np.random.choice([1, 2, 3], p=[0.7, 0.25, 0.05])),
    })

trips = pd.DataFrame(rows)

# --- deliberately inject realistic data quality issues (this is what class 6
# wants us to find, not silently fix) ---
dirty_idx = np.random.choice(trips.index, size=60, replace=False)
half = len(dirty_idx) // 4
trips.loc[dirty_idx[:half], "trip_distance"] = 0                      # zero-distance trips
trips.loc[dirty_idx[half:half*2], "fare_amount"] = -5.0               # negative fares
trips.loc[dirty_idx[half*2:half*3], "passenger_count"] = 0            # impossible passenger count
# swap pickup/dropoff so dropoff is BEFORE pickup for some rows
swap_idx = dirty_idx[half*3:]
trips.loc[swap_idx, ["tpep_pickup_datetime", "tpep_dropoff_datetime"]] = \
    trips.loc[swap_idx, ["tpep_dropoff_datetime", "tpep_pickup_datetime"]].values

# a few missing values (real files have these)
null_idx = np.random.choice(trips.index, size=20, replace=False)
trips.loc[null_idx, "passenger_count"] = np.nan

trips.to_csv(os.path.join(RAW_DIR, "trips_march2024_sample.csv"), index=False)

# ---------------------------------------------------------------------------
# 2. Taxi zone lookup (mimics real taxi_zone_lookup.csv)
# ---------------------------------------------------------------------------
zone_rows = []
zone_names = {
    "Manhattan": ["Midtown", "Harlem", "Chelsea", "SoHo", "Upper East Side"],
    "Brooklyn": ["Williamsburg", "Park Slope", "Bushwick", "DUMBO", "Bed-Stuy"],
    "Queens": ["Astoria", "Flushing", "Long Island City", "Jamaica", "Forest Hills"],
    "Bronx": ["Fordham", "Riverdale", "Mott Haven"],
    "Staten Island": ["St. George", "Tottenville"],
}
for borough, ids in boroughs.items():
    for idx, zid in enumerate(ids):
        zone_rows.append({
            "LocationID": zid,
            "Borough": borough,
            "Zone": zone_names[borough][idx],
            "service_zone": "Boro Zone" if borough != "Manhattan" else "Yellow Zone",
        })
zones = pd.DataFrame(zone_rows)
zones.to_csv(os.path.join(RAW_DIR, "taxi_zone_lookup.csv"), index=False)

# ---------------------------------------------------------------------------
# 3. Weather data — saved as a cached JSON response, shaped exactly like the
#    real Open-Meteo historical API response, so ingest.py can parse it the
#    same way whether it comes from a live call or this cached file.
# ---------------------------------------------------------------------------
dates = [start_date + timedelta(days=d) for d in range(31)]
precip = np.round(np.random.exponential(scale=1.5, size=31), 1)
precip[precip < 0.3] = 0.0
temp = np.round(np.random.normal(loc=8, scale=4, size=31), 1)

weather_json = {
    "daily": {
        "time": [d.strftime("%Y-%m-%d") for d in dates],
        "precipitation_sum": precip.tolist(),
        "temperature_2m_mean": temp.tolist(),
    }
}
with open(os.path.join(RAW_DIR, "weather_api_response_cached.json"), "w") as f:
    json.dump(weather_json, f, indent=2)

print(f"Generated {len(trips)} trip rows, {len(zones)} zones, {len(dates)} weather days into {RAW_DIR}")
