"""
model.py — Class 7 (Model workflow)

Simple relational/event model for this project:

  ENTITY: Zone           (LocationID, Borough, Zone, service_zone)
  EVENT:  Trip            (a single taxi ride: pickup event -> dropoff event)
  CONTEXT: Weather        (daily precipitation/temperature, joined by date)

  Trip (event) --pickup_zone--> Zone (entity)
  Trip (event) --dropoff_zone--> Zone (entity)
  Trip (event) --happened_on--> Weather (context, by date)

This gives us a single "clean_trips" table where each row is one trip event,
enriched with WHERE it happened (borough/zone) and WHAT the conditions were
(weather), which is what the metrics stage needs.
"""

import pandas as pd
import logging

logger = logging.getLogger("pipeline.model")


def build_trip_model(trips_df, zones_df, weather_df):
    df = trips_df.copy()

    # derived fields (the "event" attributes)
    df["trip_duration_min"] = (
        df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60
    df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour
    df["pickup_date"] = df["tpep_pickup_datetime"].dt.normalize()

    # avoid divide-by-zero for speed calc on flagged rows
    df["speed_mph"] = df["trip_distance"] / (df["trip_duration_min"] / 60)
    df["speed_mph"] = df["speed_mph"].replace([float("inf"), -float("inf")], pd.NA)

    df["fare_per_mile"] = df["fare_amount"] / df["trip_distance"].replace(0, pd.NA)

    # join pickup zone -> borough
    zones_small = zones_df[["LocationID", "Borough", "Zone"]]
    df = df.merge(
        zones_small.rename(columns={"LocationID": "PULocationID",
                                     "Borough": "pickup_borough",
                                     "Zone": "pickup_zone"}),
        on="PULocationID", how="left"
    )
    df = df.merge(
        zones_small.rename(columns={"LocationID": "DOLocationID",
                                     "Borough": "dropoff_borough",
                                     "Zone": "dropoff_zone"}),
        on="DOLocationID", how="left"
    )

    # join weather by date
    df = df.merge(weather_df, left_on="pickup_date", right_on="date", how="left")
    df["is_rainy_day"] = df["precipitation_mm"] > 1.0  # business rule: >1mm counts as "rainy"

    logger.info(f"Built trip model with {len(df)} rows and {df.shape[1]} columns")
    return df
