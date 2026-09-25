"""
ingest.py — Class 5 (Retrieve data)

This is the "retrieval" stage of the pipeline. It shows TWO retrieval modes,
as required by the assignment:

1. FILE retrieval: reading raw CSV files (trip data + zone lookup).
2. API retrieval: pulling weather data from a live API (Open-Meteo, no key
   needed). If there's no internet access (like in a sandbox), it falls
   back to a cached copy of a real API response so the pipeline still runs
   end-to-end. This fallback is logged clearly, not hidden.

Raw inputs are never modified in place — we always read from data/raw/ and
write results to data/processed/, so the original source files are preserved.
"""

import pandas as pd
import json
import os
import logging

logger = logging.getLogger("pipeline.ingest")

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")


def load_trip_data(filename="trips_march2024_sample.csv"):
    """Retrieval mode 1: file-based (CSV)."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Trip data file not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} trip records from {filename}")
    return df


def load_zone_lookup(filename="taxi_zone_lookup.csv"):
    """Retrieval mode 1 (again): file-based (CSV), separate source system
    from the trip data (this is TLC's reference/lookup data, not event data)."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Zone lookup file not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} zone lookup records from {filename}")
    return df


def fetch_weather_data(start_date="2024-03-01", end_date="2024-03-31",
                        latitude=40.71, longitude=-74.01):
    """Retrieval mode 2: API.

    Tries a live call to Open-Meteo's free historical weather API. If that
    fails (no internet, rate limit, etc.), falls back to a cached response
    saved earlier from a real call, so the pipeline is still reproducible.
    """
    try:
        import requests
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "precipitation_sum,temperature_2m_mean",
            "timezone": "America/New_York",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Fetched weather data live from Open-Meteo API")
    except Exception as e:
        logger.warning(f"Live weather API call failed ({e}); using cached sample response")
        cached_path = os.path.join(RAW_DIR, "weather_api_response_cached.json")
        with open(cached_path) as f:
            data = json.load(f)

    weather_df = pd.DataFrame({
        "date": data["daily"]["time"],
        "precipitation_mm": data["daily"]["precipitation_sum"],
        "temp_avg_c": data["daily"]["temperature_2m_mean"],
    })
    weather_df["date"] = pd.to_datetime(weather_df["date"])
    logger.info(f"Loaded {len(weather_df)} days of weather data")
    return weather_df


def check_retrieval_complete(trips_df, zones_df, weather_df):
    """Simple completeness checks — did we actually get what we expected?"""
    issues = []
    if len(trips_df) == 0:
        issues.append("Trip data is empty")
    if len(zones_df) == 0:
        issues.append("Zone lookup is empty")
    if len(weather_df) < 28:  # should have ~1 month of days
        issues.append(f"Weather data has only {len(weather_df)} days, expected ~30-31")

    if issues:
        for issue in issues:
            logger.warning(f"Retrieval completeness check failed: {issue}")
    else:
        logger.info("Retrieval completeness check passed")
    return issues
