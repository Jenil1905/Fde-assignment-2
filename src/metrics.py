"""
metrics.py — Class 7 (metrics linked to the project KPI)

Project KPI: Trip Duration & Efficiency Reliability
  (can dispatchers/planners trust how long a trip will take and what it
  will cost, by area and by condition?)

We only compute metrics on rows that passed validation (is_flagged == False),
except for metric 5, which is specifically about data quality itself.
"""

import pandas as pd
import logging

logger = logging.getLogger("pipeline.metrics")


def compute_metrics(df):
    clean = df[df["is_flagged"] == False].copy()

    # 1. Average trip duration by pickup borough
    avg_duration_by_borough = (
        clean.groupby("pickup_borough")["trip_duration_min"]
        .mean().round(1).sort_values(ascending=False)
    )

    # 2. Average speed (mph) overall and by borough — efficiency indicator
    avg_speed_by_borough = (
        clean.groupby("pickup_borough")["speed_mph"]
        .mean().round(1).sort_values(ascending=False)
    )
    overall_avg_speed = round(clean["speed_mph"].mean(), 1)

    # 3. Trip volume by hour of day — demand pattern
    volume_by_hour = clean.groupby("pickup_hour")["trip_id"].count()

    # 4. Fare per mile: rainy vs non-rainy days — ties weather into a
    #    pricing/dispatch decision
    fare_by_weather = (
        clean.groupby("is_rainy_day")["fare_per_mile"]
        .mean().round(2)
    )

    # 5. Data quality rate — % of records flagged as invalid (this is a
    #    metric about the pipeline/data itself, using the FULL dataset)
    pct_flagged = round(100 * df["is_flagged"].sum() / len(df), 1)

    metrics = {
        "avg_trip_duration_min_by_borough": avg_duration_by_borough.to_dict(),
        "avg_speed_mph_by_borough": avg_speed_by_borough.to_dict(),
        "overall_avg_speed_mph": overall_avg_speed,
        "trip_volume_by_hour": volume_by_hour.to_dict(),
        "avg_fare_per_mile_by_weather": {
            "rainy_day": fare_by_weather.get(True, None),
            "non_rainy_day": fare_by_weather.get(False, None),
        },
        "pct_records_flagged_invalid": pct_flagged,
    }

    logger.info(f"Computed metrics: {metrics}")
    return metrics


def metrics_to_table(metrics):
    """Flatten metrics dict into a simple long-format table for the
    evidence table / dashboard output required by the assignment."""
    rows = []
    for borough, val in metrics["avg_trip_duration_min_by_borough"].items():
        rows.append({"metric": "avg_trip_duration_min", "segment": borough, "value": val})
    for borough, val in metrics["avg_speed_mph_by_borough"].items():
        rows.append({"metric": "avg_speed_mph", "segment": borough, "value": val})
    rows.append({"metric": "overall_avg_speed_mph", "segment": "ALL", "value": metrics["overall_avg_speed_mph"]})
    for hour, val in metrics["trip_volume_by_hour"].items():
        rows.append({"metric": "trip_volume", "segment": f"hour_{hour}", "value": val})
    rows.append({"metric": "avg_fare_per_mile", "segment": "rainy_day",
                 "value": metrics["avg_fare_per_mile_by_weather"]["rainy_day"]})
    rows.append({"metric": "avg_fare_per_mile", "segment": "non_rainy_day",
                 "value": metrics["avg_fare_per_mile_by_weather"]["non_rainy_day"]})
    rows.append({"metric": "pct_records_flagged_invalid", "segment": "ALL",
                 "value": metrics["pct_records_flagged_invalid"]})
    return pd.DataFrame(rows)
