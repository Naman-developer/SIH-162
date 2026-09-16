"""
PS162 — Behavioral ML Prediction Engine

Loads the NEW anthropogenic XGBoost model and performs
read-only predictions.

Does NOT modify:
    backend/ml/
    PostgreSQL
    existing classifier
"""

import os
import json
import joblib
import numpy as np

from features import (
    load_behavioral_features,
    FEATURE_NAMES,
)


BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "anthropogenic_model.pkl",
)

METADATA_PATH = os.path.join(
    BASE_DIR,
    "models",
    "anthropogenic_metadata.json",
)


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)


def load_metadata():
    if not os.path.exists(METADATA_PATH):
        raise FileNotFoundError(
            f"Metadata not found: {METADATA_PATH}"
        )

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def prepare_features(df, feature_names):
    """
    Prepare the exact feature order used during training.
    """

    missing = [
        name
        for name in feature_names
        if name not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Missing prediction features: {missing}"
        )

    X = (
        df[feature_names]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .astype(np.float32)
    )

    # Same protection used during training.
    if "distance_to_facility_m" in X.columns:
        X["distance_to_facility_m"] = np.minimum(
            X["distance_to_facility_m"],
            5000,
        )

    return X


def explain_prediction(model, X_row):
    """
    Return simple feature contribution information.

    These are NOT independent probabilities.
    They are model feature-importance indicators
    for the current prediction context.
    """

    importances = model.feature_importances_

    values = X_row.to_numpy()[0]

    contributions = []

    for name, importance, value in zip(
        X_row.columns,
        importances,
        values,
    ):
        contributions.append(
            {
                "feature": name,
                "importance": round(
                    float(importance),
                    6,
                ),
                "value": round(
                    float(value),
                    6,
                ),
            }
        )

    contributions.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    return contributions[:8]


def predict_all():
    """
    Run the model against the current enriched dataset.
    Read-only.
    """

    model = load_model()
    metadata = load_metadata()

    feature_names = metadata.get(
        "feature_names",
        FEATURE_NAMES,
    )

    df = load_behavioral_features()

    X = prepare_features(
        df,
        feature_names,
    )

    probabilities = model.predict_proba(X)[:, 1]

    results = df[
        ["hotspot_id"]
    ].copy()

    results["anthropogenic_probability"] = (
        probabilities
    )

    results["decision"] = np.where(
        probabilities >= 0.5,
        "YES",
        "NO",
    )

    return results


def predict_hotspot(hotspot_id):
    """
    Predict one hotspot from the current database.
    """

    model = load_model()
    metadata = load_metadata()

    feature_names = metadata.get(
        "feature_names",
        FEATURE_NAMES,
    )

    df = load_behavioral_features()

    match = df[
        df["hotspot_id"] == hotspot_id
    ]

    if match.empty:
        raise ValueError(
            f"Hotspot {hotspot_id} not found"
        )

    X = prepare_features(
        match,
        feature_names,
    )

    probability = float(
        model.predict_proba(X)[0][1]
    )

    decision = (
        "YES"
        if probability >= 0.5
        else "NO"
    )

    explanation = explain_prediction(
        model,
        X,
    )

    return {
        "hotspot_id": int(hotspot_id),
        "anthropogenic_probability": round(
            probability,
            4,
        ),
        "decision": decision,
        "threshold": 0.5,
        "model_type": metadata.get(
            "model_type",
            "XGBoost",
        ),
        "weak_supervision": metadata.get(
            "weak_supervision",
            True,
        ),
        "top_features": explanation,
    }
def predict_custom(payload):
    """
    Run the trained anthropogenic model on custom
    user-supplied behavioral inputs.
    """

    model = load_model()
    metadata = load_metadata()

    feature_names = metadata.get(
        "feature_names",
        FEATURE_NAMES,
    )

    latitude = float(payload.get("latitude", 0))
    longitude = float(payload.get("longitude", 0))
    active_days = float(payload.get("activeDays", 0))
    nighttime_fraction = float(
        payload.get("nighttimeFraction", 0)
    )
    mean_frp = float(payload.get("meanFrp", 0))
    firms_type2_flag = float(
        payload.get("firmsType2Flag", 0)
    )

    row = {
        "latitude": latitude,
        "longitude": longitude,
        "frp": mean_frp,
        "brightness": 330.0,
        "frp_brightness_ratio": (
            mean_frp / 330.0 if mean_frp > 0 else 0
        ),
        "confidence_num": 2,
        "is_day": 1 - int(
            nighttime_fraction >= 0.5
        ),
        "hour_of_day": 12,
        "month": 10,
        "day_of_year": 274,
        "is_stubble_season": 1,
        "nighttime_fraction_facility":
            nighttime_fraction,
        "active_days_facility":
            active_days,
        "observation_frequency_facility":
            active_days,
        "days_since_first_seen": 0,
        "days_since_last_seen": 0,
        "avg_frp_facility": mean_frp,
        "max_frp_facility": mean_frp,
        "frp_vs_facility_avg": 1.0,
        "distance_to_facility_m": 500.0,
        "facility_proximity_flag": 1,
        "neighbor_count_1km_24h": 0,
        "landuse_industrial": 0,
        "landuse_agricultural": (
            1 if mean_frp < 25 else 0
        ),
        "landuse_forest": 0,
        "landuse_unknown": 1,
        "satellite_code": 21,
        "instrument_code": 1,
        "recent_7d_facility_detections":
            active_days,
    }

    import pandas as pd

    df = pd.DataFrame([row])

    X = prepare_features(
        df,
        feature_names,
    )

    probability = float(
        model.predict_proba(X)[0][1]
    )

    decision = (
        "YES"
        if probability >= 0.5
        else "NO"
    )

    explanation = explain_prediction(
        model,
        X,
    )

    return {
        "source_name": payload.get(
            "sourceName",
            "Custom Sensor Site",
        ),
        "anthropogenic_probability": round(
            probability,
            4,
        ),
        "decision": decision,
        "threshold": 0.5,
        "model_type": metadata.get(
            "model_type",
            "XGBoost",
        ),
        "weak_supervision": metadata.get(
            "weak_supervision",
            True,
        ),
        "top_features": explanation,
    }
def predict_source_type_custom(payload):
    """
    Run the separate 4-class source-type model on
    custom behavioral inputs.

    Current prototype classes:
        crop_burning
        flare
        industrial
        other
    """

    SOURCE_MODEL_PATH = os.path.join(
        BASE_DIR,
        "models",
        "source_type_model.pkl",
    )

    SOURCE_METADATA_PATH = os.path.join(
        BASE_DIR,
        "models",
        "source_type_metadata.json",
    )

    if not os.path.exists(SOURCE_MODEL_PATH):
        raise FileNotFoundError(
            f"Source type model not found: {SOURCE_MODEL_PATH}"
        )

    if not os.path.exists(SOURCE_METADATA_PATH):
        raise FileNotFoundError(
            f"Source type metadata not found: {SOURCE_METADATA_PATH}"
        )

    source_model = joblib.load(SOURCE_MODEL_PATH)

    with open(
        SOURCE_METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    feature_names = metadata["feature_names"]
    class_names = metadata["classes"]

    latitude = float(payload.get("latitude", 0))
    longitude = float(payload.get("longitude", 0))
    active_days = float(payload.get("activeDays", 0))
    nighttime_fraction = float(
        payload.get("nighttimeFraction", 0)
    )
    mean_frp = float(payload.get("meanFrp", 0))

    row = {
        "latitude": latitude,
        "longitude": longitude,
        "frp": mean_frp,
        "brightness": 330.0,
        "frp_brightness_ratio": (
            mean_frp / 330.0
            if mean_frp > 0 else 0
        ),
        "confidence_num": 2,
        "is_day": 1 - int(
            nighttime_fraction >= 0.5
        ),
        "hour_of_day": 12,
        "month": 10,
        "day_of_year": 274,
        "is_stubble_season": 1,
        "nighttime_fraction_facility": nighttime_fraction,
        "active_days_facility": active_days,
        "observation_frequency_facility": active_days,
        "days_since_first_seen": 0,
        "days_since_last_seen": 0,
        "avg_frp_facility": mean_frp,
        "max_frp_facility": mean_frp,
        "frp_vs_facility_avg": 1.0,
        "distance_to_facility_m": 500.0,
        "facility_proximity_flag": 1,
        "neighbor_count_1km_24h": 0,
        "landuse_industrial": 0,
        "landuse_agricultural": (
            1 if mean_frp < 25 else 0
        ),
        "landuse_forest": 0,
        "landuse_unknown": 1,
        "satellite_code": 21,
        "instrument_code": 1,
        "recent_7d_facility_detections": active_days,
    }

    import pandas as pd

    df = pd.DataFrame([row])

    X = (
        df[feature_names]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .astype(np.float32)
    )

    if "distance_to_facility_m" in X.columns:
        X["distance_to_facility_m"] = np.minimum(
            X["distance_to_facility_m"],
            5000,
        )

    probabilities = source_model.predict_proba(X)[0]

    predicted_index = int(
        np.argmax(probabilities)
    )

    predicted_class = class_names[predicted_index]

    class_probabilities = {
        class_name: round(
            float(probability),
            4,
        )
        for class_name, probability in zip(
            class_names,
            probabilities,
        )
    }

    ranked_classes = sorted(
        class_probabilities.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return {
        "source_name": payload.get(
            "sourceName",
            "Custom Sensor Site",
        ),
        "predicted_source_type": predicted_class,
        "confidence": round(
            float(probabilities[predicted_index]),
            4,
        ),
        "class_probabilities": class_probabilities,
        "ranked_classes": [
            {
                "class": name,
                "probability": probability,
            }
            for name, probability in ranked_classes
        ],
        "model_type": metadata.get(
            "model_type",
            "XGBoost multiclass classifier",
        ),
        "weak_supervision": metadata.get(
            "weak_supervision",
            True,
        ),
    }
if __name__ == "__main__":

    print("=" * 70)
    print(" PS162 — Behavioral ML Prediction Engine")
    print("=" * 70)

    result = predict_hotspot(94)

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    print()
    print("[ML] Prediction test complete.")
    print("[ML] Database was not modified.")