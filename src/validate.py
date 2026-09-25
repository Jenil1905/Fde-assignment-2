"""
validate.py — Class 6 (Profile & validate)

Goal: profile the raw trip data, define business-oriented validation rules,
and FLAG bad records rather than silently deleting or "fixing" them. Flagged
records are kept in a separate file so we can see exactly what we chose to
exclude from metrics, and why.
"""

import pandas as pd
import logging

logger = logging.getLogger("pipeline.validate")


def profile_trips(df):
    """Basic data profiling — what does the raw data actually look like?"""
    profile = {
        "row_count": len(df),
        "null_counts": df.isnull().sum().to_dict(),
        "trip_distance_min": df["trip_distance"].min(),
        "trip_distance_max": df["trip_distance"].max(),
        "fare_amount_min": df["fare_amount"].min(),
        "fare_amount_max": df["fare_amount"].max(),
        "passenger_count_unique": sorted(df["passenger_count"].dropna().unique().tolist()),
    }
    logger.info(f"Profile summary: {profile}")
    return profile


def validate_trips(df):
    """
    Business validation rules for a taxi trip record. Each rule flags rows
    rather than dropping them immediately, so we can review + report on
    exactly what's wrong before deciding what to exclude from metrics.

    Rules (each is a defensible, explainable business assumption):
      1. dropoff_datetime must be after pickup_datetime (a trip can't end
         before it starts)
      2. trip_distance must be > 0 (a trip with 0 distance is not a real trip)
      3. fare_amount must be >= 0 (negative fares are a data error, not a
         valid discount)
      4. passenger_count must be between 1 and 6 (NYC taxi legal max is
         typically 4-6 depending on vehicle; 0 or missing is invalid)
      5. PULocationID / DOLocationID must exist in the zone lookup table
         (an unknown zone means we can't map the trip to a borough)
    """
    df = df.copy()
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])

    df["flag_bad_time_order"] = df["tpep_dropoff_datetime"] <= df["tpep_pickup_datetime"]
    df["flag_zero_distance"] = df["trip_distance"] <= 0
    df["flag_negative_fare"] = df["fare_amount"] < 0
    df["flag_bad_passenger_count"] = (
        df["passenger_count"].isnull()
        | (df["passenger_count"] < 1)
        | (df["passenger_count"] > 6)
    )

    df["is_flagged"] = (
        df["flag_bad_time_order"]
        | df["flag_zero_distance"]
        | df["flag_negative_fare"]
        | df["flag_bad_passenger_count"]
    )

    flag_summary = {
        "bad_time_order": int(df["flag_bad_time_order"].sum()),
        "zero_distance": int(df["flag_zero_distance"].sum()),
        "negative_fare": int(df["flag_negative_fare"].sum()),
        "bad_passenger_count": int(df["flag_bad_passenger_count"].sum()),
        "total_flagged": int(df["is_flagged"].sum()),
        "total_rows": len(df),
    }
    logger.info(f"Validation summary: {flag_summary}")

    return df, flag_summary


def validate_zone_ids(trips_df, zones_df):
    """Check pickup/dropoff zone IDs exist in the lookup table."""
    valid_ids = set(zones_df["LocationID"])
    trips_df = trips_df.copy()
    trips_df["flag_unknown_pu_zone"] = ~trips_df["PULocationID"].isin(valid_ids)
    trips_df["flag_unknown_do_zone"] = ~trips_df["DOLocationID"].isin(valid_ids)
    trips_df["is_flagged"] = (
        trips_df["is_flagged"]
        | trips_df["flag_unknown_pu_zone"]
        | trips_df["flag_unknown_do_zone"]
    )
    unknown_count = int((trips_df["flag_unknown_pu_zone"] | trips_df["flag_unknown_do_zone"]).sum())
    logger.info(f"Found {unknown_count} trips with unknown pickup/dropoff zone IDs")
    return trips_df
