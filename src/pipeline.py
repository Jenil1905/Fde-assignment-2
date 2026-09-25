"""
pipeline.py — Class 8 (Dependable pipeline)

Runs the full pipeline end-to-end: ingest -> validate -> model -> metrics.

Dependability features (kept simple, student-level, but real):
  - Logging to both console and a log file (data/../logs/pipeline.log),
    so every run leaves a record of what happened.
  - Each stage wrapped in try/except with a clear error message, so a
    failure in one stage doesn't silently corrupt later stages.
  - Rerun-safe: every run overwrites the same output files in
    data/processed/ (no duplicate/append behaviour), so running it twice in
    a row gives the same result instead of stacking up old data.
  - A final PASS/FAIL summary line so it's obvious from the log whether the
    run succeeded.

Run with:  python src/pipeline.py
"""

import logging
import os
import sys
import json
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import ingest
import validate
import model
import metrics as metrics_module

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),  # append, so history is kept across runs
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline")


def run_pipeline():
    logger.info("===== PIPELINE RUN START =====")
    try:
        # ---- Stage 1: Retrieve ----
        try:
            trips_raw = ingest.load_trip_data()
            zones = ingest.load_zone_lookup()
            weather = ingest.fetch_weather_data()
            issues = ingest.check_retrieval_complete(trips_raw, zones, weather)
        except Exception as e:
            logger.error(f"RETRIEVAL STAGE FAILED: {e}")
            raise

        # ---- Stage 2: Validate ----
        try:
            profile = validate.profile_trips(trips_raw)
            trips_validated, flag_summary = validate.validate_trips(trips_raw)
            trips_validated = validate.validate_zone_ids(trips_validated, zones)
            flagged = trips_validated[trips_validated["is_flagged"]]
            flagged.to_csv(os.path.join(PROCESSED_DIR, "flagged_records.csv"), index=False)
            logger.info(f"Saved {len(flagged)} flagged records for review")
        except Exception as e:
            logger.error(f"VALIDATION STAGE FAILED: {e}")
            raise

        # ---- Stage 3: Model ----
        try:
            trip_model = model.build_trip_model(trips_validated, zones, weather)
            trip_model.to_csv(os.path.join(PROCESSED_DIR, "trips_modeled.csv"), index=False)
        except Exception as e:
            logger.error(f"MODELING STAGE FAILED: {e}")
            raise

        # ---- Stage 4: Metrics ----
        try:
            computed_metrics = metrics_module.compute_metrics(trip_model)
            metrics_table = metrics_module.metrics_to_table(computed_metrics)
            metrics_table.to_csv(os.path.join(PROCESSED_DIR, "metrics_output.csv"), index=False)
            with open(os.path.join(PROCESSED_DIR, "metrics_output.json"), "w") as f:
                json.dump(computed_metrics, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"METRICS STAGE FAILED: {e}")
            raise

        logger.info("===== PIPELINE RUN SUCCEEDED =====")
        return True

    except Exception as e:
        logger.error(f"===== PIPELINE RUN FAILED: {e} =====")
        return False


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
