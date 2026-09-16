from fastapi import FastAPI,Body
from fastapi.middleware.cors import CORSMiddleware

import psycopg2
import os
import urllib.parse as up
import requests
import csv
import io
import json
import sys
from pathlib import Path

ML_DIR = Path("/ml")

if str(ML_DIR) not in sys.path:
    sys.path.append(str(ML_DIR))

from predict import (
    predict_hotspot,
    predict_custom,
    predict_source_type_custom,
)

from pathlib import Path
from datetime import date as dt

from dotenv import load_dotenv


load_dotenv()


DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fireuser:firepass@db:5432/firedb"
)

STATUS_FILE = Path(__file__).resolve().parent / "data_status.json"


app = FastAPI(title="PS162 Fire Detection API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    r = up.urlparse(DB_URL)

    return psycopg2.connect(
        host=r.hostname,
        port=r.port or 5432,
        dbname=r.path.lstrip("/"),
        user=r.username,
        password=r.password
    )


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE INTELLIGENCE SCORING
# ─────────────────────────────────────────────────────────────────────────────

def calculate_source_score(
    active_days,
    avg_frp,
    max_frp,
    facility
):
    """
    Rule-based industrial source intelligence score.

    This is NOT an ML probability.
    It is a transparent prototype scoring model.
    """

    # Persistence
    persistence_score = min(
        active_days / 30.0,
        1.0
    )

    # Average FRP
    avg_frp_score = min(
        avg_frp / 50.0,
        1.0
    )

    # Maximum FRP
    peak_frp_score = min(
        max_frp / 100.0,
        1.0
    )

    # Facility association
    facility_score = (
        1.0
        if facility
        else 0.0
    )

    # Weighted score
    score = (
        persistence_score * 0.45
        + avg_frp_score * 0.25
        + peak_frp_score * 0.15
        + facility_score * 0.15
    )

    score = round(
        min(score, 1.0),
        3
    )

    # Tier
    if score >= 0.80:
        tier = "A"
        tier_label = "Confirmed"

    elif score >= 0.60:
        tier = "B"
        tier_label = "Probable"

    elif score >= 0.40:
        tier = "C"
        tier_label = "Review Queue"

    else:
        tier = "D"
        tier_label = "Low Confidence"

    # Explainability
    reasons = []

    if persistence_score >= 0.70:
        reasons.append("High persistence")

    elif persistence_score >= 0.30:
        reasons.append("Moderate persistence")

    if avg_frp_score >= 0.70:
        reasons.append("High average FRP")

    if peak_frp_score >= 0.70:
        reasons.append("High peak FRP")

    if facility:
        reasons.append("Facility association")

    return (
        score,
        tier,
        tier_label,
        reasons
    )


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ─────────────────────────────────────────────────────────────────────────────
# DATA STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/data-status")
def get_data_status():

    if not STATUS_FILE.exists():
        return {
            "mode": "UNKNOWN",
            "source": None,
            "rows": 0,
            "message": "No ingestion status available"
        }

    try:
        return json.loads(
            STATUS_FILE.read_text()
        )

    except Exception as e:
        return {
            "mode": "UNKNOWN",
            "source": None,
            "rows": 0,
            "message": str(e)
        }


# ─────────────────────────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/stats")
def get_stats():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            predicted_class,
            COUNT(*)
        FROM classified_hotspots
        GROUP BY predicted_class
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "class_counts": {
            r[0]: r[1]
            for r in rows
        },
        "total": sum(
            r[1]
            for r in rows
        )
    }


# ─────────────────────────────────────────────────────────────────────────────
# HOTSPOTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/hotspots")
def get_hotspots(cls: str = None):

    conn = get_conn()
    cur = conn.cursor()

    where = (
        "WHERE c.predicted_class = %s"
        if cls
        else ""
    )

    params = (
        [cls]
        if cls
        else []
    )

    query = """
        SELECT
            r.id,
            r.latitude,
            r.longitude,
            r.brightness,
            r.frp,
            r.acq_date::text,
            c.predicted_class,
            c.confidence_score,
            e.distance_m,
            e.landuse_class,
            e.nearest_facility_name
        FROM raw_hotspots r
        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id
        JOIN classified_hotspots c
            ON c.enriched_id = e.id
        {}
        LIMIT 2000
    """.format(where)

    cur.execute(
        query,
        params
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    features = []

    for r in rows:

        features.append({
            "type": "Feature",

            "geometry": {
                "type": "Point",
                "coordinates": [
                    r[2],
                    r[1]
                ]
            },

            "properties": {
                "id": r[0],
                "brightness": r[3],
                "frp": r[4],
                "date": r[5],
                "class": r[6],
                "confidence": r[7],
                "distance_m": r[8],
                "landuse": r[9],
                "facility": r[10]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


# ─────────────────────────────────────────────────────────────────────────────
# TREND
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/trend")
def get_trend():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.acq_date::text,
            c.predicted_class,
            COUNT(*) AS cnt
        FROM raw_hotspots r

        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id

        JOIN classified_hotspots c
            ON c.enriched_id = e.id

        WHERE
            r.acq_date >= CURRENT_DATE - INTERVAL '30 days'
            AND r.acq_date <= CURRENT_DATE

        GROUP BY
            r.acq_date,
            c.predicted_class

        ORDER BY
            r.acq_date
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    by_date = {}

    for date_value, cls, cnt in rows:

        if date_value not in by_date:
            by_date[date_value] = {
                "date": date_value
            }

        by_date[date_value][cls] = cnt

    return {
        "trend": list(
            by_date.values()
        )
    }


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENT INDUSTRIAL SOURCES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/hotspots/{hotspot_id}/explain")
def explain_hotspot(hotspot_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.id,
            r.brightness,
            r.frp,
            r.acq_date::text,

            c.predicted_class,
            c.confidence_score,

            e.distance_m,
            e.landuse_class,
            e.nearest_facility_name

        FROM raw_hotspots r
        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id
        JOIN classified_hotspots c
            ON c.enriched_id = e.id

        WHERE r.id = %s
        LIMIT 1
    """, (hotspot_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Hotspot not found"
        )

    (
        hotspot_id,
        brightness,
        frp,
        acq_date,
        predicted_class,
        confidence,
        distance_m,
        landuse_class,
        facility
    ) = row

    brightness = float(brightness or 0)
    frp = float(frp or 0)
    confidence = float(confidence or 0)
    distance_m = float(distance_m) if distance_m is not None else None

    predicted_class = predicted_class or "other"
    landuse_class = (landuse_class or "unknown").lower()

    factors = []

    # -------------------------------------------------
    # 1. LAND-USE ALIGNMENT
    # -------------------------------------------------
    landuse_match = False

    if predicted_class == "industrial":
        landuse_match = landuse_class == "industrial"
    elif predicted_class == "agricultural":
        landuse_match = landuse_class in (
            "agricultural",
            "agriculture",
            "cropland"
        )
    elif predicted_class == "forest":
        landuse_match = landuse_class in (
            "forest",
            "woodland"
        )

    if landuse_match:
        landuse_impact = 1.0
        landuse_reason = (
            f"Land-use context supports {predicted_class} classification"
        )
    elif landuse_class != "unknown":
        landuse_impact = 0.35
        landuse_reason = (
            f"Land-use context is {landuse_class}, "
            f"which provides weaker support"
        )
    else:
        landuse_impact = 0.15
        landuse_reason = "Land-use context unavailable"

    factors.append({
        "name": "Land-use alignment",
        "value": landuse_class,
        "impact": round(landuse_impact, 2),
        "reason": landuse_reason
    })

    # -------------------------------------------------
    # 2. FACILITY PROXIMITY
    # -------------------------------------------------
    if distance_m is not None:
        if distance_m <= 250:
            facility_impact = 1.0
            facility_reason = (
                f"Very close to facility ({round(distance_m)} m)"
            )
        elif distance_m <= 500:
            facility_impact = 0.8
            facility_reason = (
                f"Close to facility ({round(distance_m)} m)"
            )
        elif distance_m <= 1000:
            facility_impact = 0.6
            facility_reason = (
                f"Within 1 km of facility ({round(distance_m)} m)"
            )
        else:
            facility_impact = 0.15
            facility_reason = (
                f"Facility is relatively distant ({round(distance_m)} m)"
            )
    else:
        facility_impact = 0.0
        facility_reason = "No nearby facility association"

    factors.append({
        "name": "Facility proximity",
        "value": (
            f"{round(distance_m)} m"
            if distance_m is not None
            else "None"
        ),
        "impact": round(facility_impact, 2),
        "reason": facility_reason
    })

    # -------------------------------------------------
    # 3. FRP CONTRIBUTION
    # -------------------------------------------------
    frp_impact = min(frp / 50.0, 1.0)

    if frp >= 50:
        frp_reason = f"High thermal intensity ({frp:.2f} MW)"
    elif frp >= 20:
        frp_reason = f"Moderate thermal intensity ({frp:.2f} MW)"
    else:
        frp_reason = f"Lower thermal intensity ({frp:.2f} MW)"

    factors.append({
        "name": "FRP",
        "value": f"{frp:.2f} MW",
        "impact": round(frp_impact, 2),
        "reason": frp_reason
    })

    # -------------------------------------------------
    # 4. BRIGHTNESS CONTRIBUTION
    # -------------------------------------------------
    brightness_impact = max(
        0.0,
        min((brightness - 280.0) / 60.0, 1.0)
    )

    if brightness >= 320:
        brightness_reason = (
            f"High thermal brightness ({brightness:.2f} K)"
        )
    elif brightness >= 300:
        brightness_reason = (
            f"Moderate thermal brightness ({brightness:.2f} K)"
        )
    else:
        brightness_reason = (
            f"Lower thermal brightness ({brightness:.2f} K)"
        )

    factors.append({
        "name": "Brightness",
        "value": f"{brightness:.2f} K",
        "impact": round(brightness_impact, 2),
        "reason": brightness_reason
    })

    # -------------------------------------------------
    # HUMAN-READABLE REASONS
    # -------------------------------------------------
    reasons = []

    if landuse_match:
        reasons.append(
            f"Land use supports {predicted_class} activity"
        )

    if distance_m is not None and distance_m <= 1000:
        if facility:
            reasons.append(
                f"Associated with {facility} at {round(distance_m)} m"
            )
        else:
            reasons.append(
                f"Nearby facility within {round(distance_m)} m"
            )

    if frp >= 20:
        reasons.append(
            f"Thermal intensity is {frp:.2f} MW"
        )

    if brightness >= 310:
        reasons.append(
            f"Brightness is elevated at {brightness:.2f} K"
        )

    if not reasons:
        reasons.append(
            "Classification is based on the available contextual features"
        )

    return {
        "hotspot_id": hotspot_id,
        "classification": predicted_class,
        "confidence": round(confidence, 4),
        "model_type": "transparent feature attribution",
        "model_note": (
            "Feature contributions shown here are a rule-based "
            "explainability layer for the current classifier pipeline. "
            "They are not independent ML probabilities."
        ),
        "factors": factors,
        "reasons": reasons
    }

@app.get("/hotspots/{hotspot_id}/risk")
def get_hotspot_risk(hotspot_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.id,
            r.frp,
            r.brightness,
            c.predicted_class,
            c.confidence_score,
            e.distance_m,
            e.landuse_class,
            e.nearest_facility_name
        FROM raw_hotspots r
        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id
        JOIN classified_hotspots c
            ON c.enriched_id = e.id
        WHERE r.id = %s
        LIMIT 1
    """, (hotspot_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return {
            "hotspot_id": hotspot_id,
            "risk_score": 0,
            "priority": "UNKNOWN",
            "reasons": ["Hotspot not found"]
        }

    (
        hotspot_id,
        frp,
        brightness,
        predicted_class,
        confidence,
        distance_m,
        landuse,
        facility
    ) = row

    frp = float(frp or 0)
    brightness = float(brightness or 0)
    confidence = float(confidence or 0)
    distance_m = float(distance_m) if distance_m is not None else None

    score = 0
    reasons = []

    # Thermal intensity
    if frp >= 80:
        score += 30
        reasons.append("Very high thermal intensity")
    elif frp >= 50:
        score += 20
        reasons.append("High thermal intensity")
    elif frp >= 25:
        score += 10
        reasons.append("Moderate thermal intensity")

    # Industrial classification
    if predicted_class == "industrial":
        score += 25
        reasons.append("Industrial fire classification")

    # Land-use risk
    if landuse == "industrial":
        score += 15
        reasons.append("Industrial land-use context")
    elif landuse == "forest":
        score += 12
        reasons.append("Forest land-use context")
    elif landuse == "agricultural":
        score += 6
        reasons.append("Agricultural land-use context")

    # Facility proximity
    if distance_m is not None:
        if distance_m <= 100:
            score += 20
            reasons.append("Very close to critical facility")
        elif distance_m <= 500:
            score += 12
            reasons.append("Close to facility")
        elif distance_m <= 1000:
            score += 6
            reasons.append("Within 1 km of facility")

    # Confidence adjustment
    if confidence >= 0.95:
        score += 5

    score = min(score, 100)

    if score >= 75:
        priority = "CRITICAL"
    elif score >= 50:
        priority = "HIGH"
    elif score >= 25:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return {
        "hotspot_id": hotspot_id,
        "risk_score": score,
        "priority": priority,
        "classification": predicted_class,
        "confidence": round(confidence, 4),
        "frp": round(frp, 2),
        "brightness": round(brightness, 2),
        "distance_m": round(distance_m, 1) if distance_m is not None else None,
        "landuse": landuse or "unknown",
        "facility": facility or None,
        "reasons": reasons
    }

@app.get("/persistent-sources")
def get_persistent_sources():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            e.nearest_facility_name,
            ROUND(AVG(r.latitude)::numeric, 6) AS lat,
            ROUND(AVG(r.longitude)::numeric, 6) AS lon,
            COUNT(DISTINCT r.acq_date) AS active_days,
            ROUND(AVG(r.frp)::numeric, 2) AS avg_frp,
            ROUND(MAX(r.frp)::numeric, 2) AS max_frp,
            COUNT(*) AS detection_count

        FROM raw_hotspots r

        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id

        JOIN classified_hotspots c
            ON c.enriched_id = e.id

        WHERE
            c.predicted_class = 'industrial'
            AND e.distance_m < 1000
            AND e.nearest_facility_name IS NOT NULL

        GROUP BY
            e.nearest_facility_name

        HAVING
            COUNT(DISTINCT r.acq_date) >= 3

        ORDER BY
            active_days DESC,
            max_frp DESC

        LIMIT 20
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    sources = []

    for r in rows:

        facility = r[0]
        lat = float(r[1])
        lon = float(r[2])
        active_days = int(r[3])
        avg_frp = float(r[4])
        max_frp = float(r[5])
        detection_count = int(r[6])

        score, tier, tier_label, reasons = calculate_source_score(
            active_days,
            avg_frp,
            max_frp,
            facility
        )

        sources.append({
            "lat": lat,
            "lon": lon,
            "facility": facility,
            "active_days": active_days,
            "avg_frp": avg_frp,
            "max_frp": max_frp,
            "detection_count": detection_count,
            "source_score": score,
            "tier": tier,
            "tier_label": tier_label,
            "reasons": reasons,
        })

    return {
        "sources": sources
    }
@app.get("/persistent-source-history")
def get_persistent_source_history(facility: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.acq_date::text AS date,
            COUNT(*) AS detections,
            ROUND(AVG(r.frp)::numeric, 2) AS avg_frp,
            ROUND(MAX(r.frp)::numeric, 2) AS max_frp
        FROM raw_hotspots r
        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id
        JOIN classified_hotspots c
            ON c.enriched_id = e.id
        WHERE c.predicted_class = 'industrial'
          AND e.nearest_facility_name = %s
        GROUP BY r.acq_date
        ORDER BY r.acq_date
    """, (facility,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "facility": facility,
        "history": [
            {
                "date": row[0],
                "detections": int(row[1]),
                "avg_frp": float(row[2] or 0),
                "max_frp": float(row[3] or 0)
            }
            for row in rows
        ]
    }
@app.get("/persistent-source-anomaly")
def get_persistent_source_anomaly(facility: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.acq_date::text AS date,
            ROUND(AVG(r.frp)::numeric, 2) AS avg_frp,
            ROUND(MAX(r.frp)::numeric, 2) AS max_frp
        FROM raw_hotspots r
        JOIN enriched_hotspots e
            ON e.raw_hotspot_id = r.id
        JOIN classified_hotspots c
            ON c.enriched_id = e.id
        WHERE c.predicted_class = 'industrial'
          AND e.nearest_facility_name = %s
        GROUP BY r.acq_date
        ORDER BY r.acq_date
    """, (facility,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        return {
            "facility": facility,
            "anomaly": False,
            "severity": "NORMAL",
            "message": "No historical source data available."
        }

    # Latest observation
    latest_date = rows[-1][0]
    current_frp = float(rows[-1][2] or 0)

    # Use all previous observations as the historical baseline
    historical_rows = rows[:-1]

    if not historical_rows:
        return {
            "facility": facility,
            "anomaly": False,
            "severity": "NORMAL",
            "date": latest_date,
            "current_frp": round(current_frp, 2),
            "baseline_frp": round(current_frp, 2),
            "change_percent": 0,
            "observations_used": 0
        }

    baseline_frp = sum(
        float(row[1] or 0)
        for row in historical_rows
    ) / len(historical_rows)

    if baseline_frp <= 0:
        change_percent = 0
    else:
        change_percent = (
            (current_frp - baseline_frp)
            / baseline_frp
        ) * 100

    if change_percent >= 100:
        severity = "HIGH"
    elif change_percent >= 50:
        severity = "MEDIUM"
    else:
        severity = "NORMAL"

    return {
        "facility": facility,
        "anomaly": change_percent >= 50,
        "severity": severity,
        "date": latest_date,
        "current_frp": round(current_frp, 2),
        "baseline_frp": round(baseline_frp, 2),
        "change_percent": round(change_percent, 1),
        "observations_used": len(historical_rows)
    }
# ─────────────────────────────────────────────────────────────────────────────
# LIVE INGESTION
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/ingest-live")
def ingest_live():

    api_key = os.getenv(
        "FIRMS_API_KEY"
    )

    if not api_key:
        return {
            "error": "FIRMS_API_KEY is not configured"
        }

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        + api_key
        + "/VIIRS_SNPP_NRT/"
        + "73.8,29.5,77.5,32.0/2"
    )

    try:

        resp = requests.get(
            url,
            timeout=30
        )

        resp.raise_for_status()

    except Exception as e:

        return {
            "error": str(e)
        }

    reader = csv.DictReader(
        io.StringIO(
            resp.text
        )
    )

    rows = list(
        reader
    )

    if not rows:
        return {
            "inserted": 0
        }

    conn = get_conn()
    cur = conn.cursor()

    inserted = 0

    for r in rows:

        try:

            lat = float(
                r["latitude"]
            )

            lon = float(
                r["longitude"]
            )

            cur.execute(
                """
                INSERT INTO raw_hotspots (
                    geom,
                    latitude,
                    longitude,
                    brightness,
                    frp,
                    confidence,
                    acq_date,
                    acq_time,
                    satellite,
                    instrument,
                    daynight
                )
                VALUES (
                    ST_SetSRID(
                        ST_MakePoint(%s, %s),
                        4326
                    ),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT DO NOTHING
                """,
                (
                    lon,
                    lat,
                    lat,
                    lon,
                    float(
                        r.get("bright_ti4")
                        or 0
                    ),
                    float(
                        r.get("frp")
                        or 0
                    ),
                    r.get(
                        "confidence",
                        "n"
                    ),
                    r.get(
                        "acq_date",
                        str(dt.today())
                    ),
                    r.get(
                        "acq_time",
                        "0000"
                    ),
                    r.get(
                        "satellite",
                        "N"
                    ),
                    "VIIRS",
                    r.get(
                        "daynight",
                        ""
                    )
                )
            )

            inserted += 1

        except Exception:
            continue

    conn.commit()

    cur.close()
    conn.close()

    return {
        "inserted": inserted,
        "total_rows": len(rows)
    }
@app.get("/ml/predict/{hotspot_id}")
def ml_predict_hotspot(hotspot_id: int):
    try:
        return predict_hotspot(hotspot_id)

    except ValueError as e:
        return {
            "error": str(e)
        }

    except Exception as e:
        print(f"[ML API] Prediction error: {e}")

        return {
            "error": "ML prediction failed"
        }

@app.post("/ml/predict-custom")
def ml_predict_custom(payload: dict = Body(...)):
    try:
        anthropogenic = predict_custom(payload)
        source_type = predict_source_type_custom(payload)

        return {
            **anthropogenic,
            "source_type_prediction": source_type,
        }

    except Exception as e:
        print(f"[ML API] Custom prediction error: {e}")

        return {
            "error": "Custom ML prediction failed",
            "detail": str(e),
        }