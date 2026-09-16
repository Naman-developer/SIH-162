"""
PS162 Fire Intelligence
New Behavioral ML Feature Engine

IMPORTANT:
- Read-only feature extraction.
- Does NOT modify the existing backend/ml classifier.
- Does NOT write anything to PostgreSQL.
- Produces a fixed 32-feature vector for the new ML models.
"""

import os
import urllib.parse as up

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv


load_dotenv()

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fireuser:firepass@localhost:5432/firedb",
)


# ============================================================
# FIXED 32-FEATURE CONTRACT
# ============================================================

FEATURE_NAMES = [
    "latitude",
    "longitude",
    "frp",
    "brightness",
    "frp_brightness_ratio",
    "confidence_num",
    "is_day",
    "hour_of_day",
    "month",
    "day_of_year",
    "is_stubble_season",
    "nighttime_fraction_facility",
    "active_days_facility",
    "observation_frequency_facility",
    "days_since_first_seen",
    "days_since_last_seen",
    "avg_frp_facility",
    "max_frp_facility",
    "frp_vs_facility_avg",
    "distance_to_facility_m",
    "facility_proximity_flag",
    "neighbor_count_1km_24h",
    "ndvi_value",
    "ndbi_value",
    "ndwi_value",
    "landuse_industrial",
    "landuse_agricultural",
    "landuse_forest",
    "landuse_unknown",
    "satellite_code",
    "instrument_code",
    "recent_7d_facility_detections",
]


def get_conn():
    """Create a PostgreSQL connection."""
    parsed = up.urlparse(DB_URL)

    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )


# ============================================================
# MAIN FEATURE EXTRACTION
# ============================================================

def load_behavioral_features():
    """
    Read hotspot + enrichment data and construct the
    fixed 32-feature behavioral ML dataset.

    This function is READ ONLY.
    """

    conn = get_conn()

    query = """
    WITH latest_date AS (
        SELECT MAX(acq_date) AS max_date
        FROM raw_hotspots
        WHERE acq_date IS NOT NULL
    ),

    facility_history AS (
        SELECT
            e.nearest_facility_name AS facility_name,

            COUNT(*) AS facility_detection_count,

            COUNT(DISTINCT r.acq_date) AS active_days_facility,

            MIN(r.acq_date) AS first_seen_facility,

            MAX(r.acq_date) AS last_seen_facility,

            AVG(COALESCE(r.frp, 0)) AS avg_frp_facility,

            MAX(COALESCE(r.frp, 0)) AS max_frp_facility,

            SUM(
                CASE
                    WHEN r.daynight = 'N' THEN 1
                    ELSE 0
                END
            )::FLOAT
            / NULLIF(COUNT(*), 0) AS nighttime_fraction_facility,

            SUM(
                CASE
                    WHEN r.acq_date >= (
                        SELECT max_date
                        FROM latest_date
                    ) - INTERVAL '6 days'
                    THEN 1
                    ELSE 0
                END
            ) AS recent_7d_facility_detections

        FROM raw_hotspots r
        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id

        WHERE e.nearest_facility_name IS NOT NULL
          AND e.nearest_facility_name <> ''
          AND e.nearest_facility_name <> 'Unknown Facility'

        GROUP BY e.nearest_facility_name
    )

    SELECT
        r.id AS hotspot_id,

        -- ----------------------------------------------------
        -- LOCATION
        -- ----------------------------------------------------

        COALESCE(r.latitude, 0) AS latitude,

        COALESCE(r.longitude, 0) AS longitude,

        -- ----------------------------------------------------
        -- THERMAL SIGNAL
        -- ----------------------------------------------------

        COALESCE(r.frp, 0) AS frp,

        COALESCE(r.brightness, 300) AS brightness,

        CASE
            WHEN COALESCE(r.brightness, 0) > 0
            THEN COALESCE(r.frp, 0)
                 / r.brightness
            ELSE 0
        END AS frp_brightness_ratio,

        -- ----------------------------------------------------
        -- SENSOR CONFIDENCE
        -- ----------------------------------------------------

        CASE LOWER(COALESCE(r.confidence, ''))
            WHEN 'high' THEN 3
            WHEN 'h' THEN 3
            WHEN 'medium' THEN 2
            WHEN 'n' THEN 2
            WHEN 'low' THEN 1
            ELSE 1
        END AS confidence_num,

        -- ----------------------------------------------------
        -- TIME FEATURES
        -- ----------------------------------------------------

        CASE
            WHEN r.daynight = 'D' THEN 1
            ELSE 0
        END AS is_day,

        COALESCE(
            EXTRACT(
                HOUR FROM
                TO_TIMESTAMP(
                    LPAD(COALESCE(r.acq_time, '120000'), 6, '0'),
                    'HH24MISS'
                )
            ),
            12
        ) AS hour_of_day,

        COALESCE(
            EXTRACT(MONTH FROM r.acq_date),
            10
        ) AS month,

        COALESCE(
            EXTRACT(DOY FROM r.acq_date),
            274
        ) AS day_of_year,

        CASE
            WHEN EXTRACT(MONTH FROM r.acq_date) IN (10, 11)
            THEN 1
            ELSE 0
        END AS is_stubble_season,

        -- ----------------------------------------------------
        -- FACILITY BEHAVIOR
        -- ----------------------------------------------------

        COALESCE(
            fh.nighttime_fraction_facility,
            0
        ) AS nighttime_fraction_facility,

        COALESCE(
            fh.active_days_facility,
            0
        ) AS active_days_facility,

        CASE
            WHEN COALESCE(fh.active_days_facility, 0) > 0
            THEN
                fh.facility_detection_count::FLOAT
                / fh.active_days_facility
            ELSE 0
        END AS observation_frequency_facility,

        CASE
            WHEN fh.first_seen_facility IS NOT NULL
            THEN
                GREATEST(
                    (
                        SELECT max_date
                        FROM latest_date
                    ) - fh.first_seen_facility,
                    0
                )
            ELSE 0
        END AS days_since_first_seen,

        CASE
            WHEN fh.last_seen_facility IS NOT NULL
            THEN
                GREATEST(
                    (
                        SELECT max_date
                        FROM latest_date
                    ) - fh.last_seen_facility,
                    0
                )
            ELSE 9999
        END AS days_since_last_seen,

        COALESCE(
            fh.avg_frp_facility,
            0
        ) AS avg_frp_facility,

        COALESCE(
            fh.max_frp_facility,
            0
        ) AS max_frp_facility,

        CASE
            WHEN COALESCE(fh.avg_frp_facility, 0) > 0
            THEN
                COALESCE(r.frp, 0)
                / fh.avg_frp_facility
            ELSE 0
        END AS frp_vs_facility_avg,

        -- ----------------------------------------------------
        -- SPATIAL CONTEXT
        -- ----------------------------------------------------

        COALESCE(
            e.distance_m,
            99999
        ) AS distance_to_facility_m,

        CASE
            WHEN e.distance_m IS NOT NULL
             AND e.distance_m <= 500
            THEN 1
            ELSE 0
        END AS facility_proximity_flag,

        COALESCE(
            e.neighbor_count_1km_24h,
            0
        ) AS neighbor_count_1km_24h,

        -- ----------------------------------------------------
        -- ENVIRONMENT
        -- ----------------------------------------------------

        COALESCE(e.ndvi_value, 0) AS ndvi_value,

        COALESCE(e.ndbi_value, 0) AS ndbi_value,

        COALESCE(e.ndwi_value, 0) AS ndwi_value,

        CASE
            WHEN LOWER(COALESCE(e.landuse_class, 'unknown'))
                 = 'industrial'
            THEN 1
            ELSE 0
        END AS landuse_industrial,

        CASE
            WHEN LOWER(COALESCE(e.landuse_class, 'unknown'))
                 IN ('agricultural', 'farmland')
            THEN 1
            ELSE 0
        END AS landuse_agricultural,

        CASE
            WHEN LOWER(COALESCE(e.landuse_class, 'unknown'))
                 = 'forest'
            THEN 1
            ELSE 0
        END AS landuse_forest,

        CASE
            WHEN LOWER(COALESCE(e.landuse_class, 'unknown'))
                 NOT IN (
                     'industrial',
                     'agricultural',
                     'farmland',
                     'forest'
                 )
            THEN 1
            ELSE 0
        END AS landuse_unknown,

        -- ----------------------------------------------------
        -- SENSOR IDENTITY
        -- ----------------------------------------------------

        CASE
            WHEN UPPER(COALESCE(r.satellite, ''))
                 LIKE '%NOAA20%'
            THEN 20

            WHEN UPPER(COALESCE(r.satellite, ''))
                 LIKE '%NOAA21%'
            THEN 21

            WHEN UPPER(COALESCE(r.satellite, ''))
                 LIKE '%SNPP%'
            THEN 22

            ELSE 0
        END AS satellite_code,

        CASE
            WHEN UPPER(COALESCE(r.instrument, ''))
                 LIKE '%VIIRS%'
            THEN 1

            WHEN UPPER(COALESCE(r.instrument, ''))
                 LIKE '%MODIS%'
            THEN 2

            ELSE 0
        END AS instrument_code,

        -- ----------------------------------------------------
        -- RECENT SOURCE ACTIVITY
        -- ----------------------------------------------------

        COALESCE(
            fh.recent_7d_facility_detections,
            0
        ) AS recent_7d_facility_detections

    FROM raw_hotspots r

    JOIN enriched_hotspots e
        ON e.raw_hotspot_id = r.id

    LEFT JOIN facility_history fh
        ON fh.facility_name =
        e.nearest_facility_name

    WHERE r.acq_date IS NOT NULL
    """

    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    # --------------------------------------------------------
    # Numeric cleanup
    # --------------------------------------------------------

    for column in FEATURE_NAMES:
        if column not in df.columns:
            raise RuntimeError(
                f"Missing required feature column: {column}"
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df[FEATURE_NAMES] = (
        df[FEATURE_NAMES]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    print(
        f"[ML FEATURES] Loaded {len(df):,} hotspot observations."
    )

    print(
        f"[ML FEATURES] Feature count: "
        f"{len(FEATURE_NAMES)}"
    )

    return df


# ============================================================
# FEATURE MATRIX
# ============================================================

def build_feature_matrix(df):
    """
    Return the numeric matrix used by the ML models.
    """

    X = df[FEATURE_NAMES].astype(np.float32)

    return X.to_numpy()


# ============================================================
# READ-ONLY TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 65)
    print(" PS162 — Behavioral ML Feature Engine")
    print("=" * 65)

    df = load_behavioral_features()

    X = build_feature_matrix(df)

    print()
    print("Feature names:")
    for index, name in enumerate(FEATURE_NAMES, start=1):
        print(f"  {index:02d}. {name}")

    print()
    print(f"Dataset shape: {X.shape}")

    if len(df) > 0:
        print()
        print("First hotspot:")
        print(
            df[
                ["hotspot_id"] + FEATURE_NAMES
            ].iloc[0].to_string()
        )

    print()
    print("[ML FEATURES] Read-only test complete.")