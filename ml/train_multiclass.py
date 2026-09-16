"""
PS162 — 5-Class Source Type ML Prototype

Classes:
    industrial
    crop_burning
    forest
    flare
    other

IMPORTANT:
- Separate from ml/train.py
- Does NOT modify backend/ml/
- Does NOT modify the existing anthropogenic model
- Uses weak labels for prototype/demo purposes
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import psycopg2
import urllib.parse as up

from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier


BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "source_type_model.pkl",
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "source_type_metadata.json",
)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fireuser:firepass@localhost:5432/firedb",
)


# ============================================================
# FEATURES USED BY THE MODEL
# ============================================================

TRAIN_FEATURES = [
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
    "landuse_industrial",
    "landuse_agricultural",
    "landuse_forest",
    "landuse_unknown",
    "satellite_code",
    "instrument_code",
    "recent_7d_facility_detections",
]


def get_conn():
    parsed = up.urlparse(DB_URL)

    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )


# ============================================================
# LOAD EXISTING CLASSIFICATION
# ============================================================

def load_existing_classes():

    conn = get_conn()

    query = """
    SELECT
        r.id AS hotspot_id,
        c.predicted_class
    FROM raw_hotspots r
    JOIN enriched_hotspots e
        ON e.raw_hotspot_id = r.id
    JOIN classified_hotspots c
        ON c.enriched_id = e.id
    WHERE c.predicted_class IS NOT NULL
    """

    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    return df


# ============================================================
# BUILD 5-CLASS WEAK LABELS
# ============================================================

def build_source_labels(df):

    labels = []

    for _, row in df.iterrows():

        base_class = str(
            row["predicted_class"]
        ).lower()

        frp = float(row["frp"])

        night_fraction = float(
            row["nighttime_fraction_facility"]
        )

        active_days = float(
            row["active_days_facility"]
        )

        facility_distance = float(
            row["distance_to_facility_m"]
        )

        industrial_landuse = (
            row["landuse_industrial"] == 1
        )

        agricultural_landuse = (
            row["landuse_agricultural"] == 1
        )

        forest_landuse = (
            row["landuse_forest"] == 1
        )

        # ----------------------------------------------------
        # FOREST
        # ----------------------------------------------------

        if forest_landuse:

            labels.append("forest")
            continue

        # ----------------------------------------------------
        # CROP BURNING
        # ----------------------------------------------------

        if (
            agricultural_landuse
            and row["is_stubble_season"] == 1
            and frp < 35
        ):
            labels.append("crop_burning")
            continue

        # ----------------------------------------------------
        # FLARE
        #
        # Prototype weak rule:
        # Persistent + high FRP + nighttime + facility
        # ----------------------------------------------------

        if (
            active_days >= 10
            and night_fraction >= 0.60
            and frp >= 40
            and facility_distance < 1500
        ):
            labels.append("flare")
            continue

        # ----------------------------------------------------
        # INDUSTRIAL
        # ----------------------------------------------------

        if (
            base_class == "industrial"
            or industrial_landuse
            or facility_distance < 500
        ):
            labels.append("industrial")
            continue

        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        labels.append("other")

    df = df.copy()
    df["source_type"] = labels

    return df


# ============================================================
# BUILD FEATURE MATRIX
# ============================================================

def build_X(df):

    X = (
        df[TRAIN_FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .astype(np.float32)
    )

    # Replace sentinel distance with a capped value.
    if "distance_to_facility_m" in X.columns:
        X["distance_to_facility_m"] = np.minimum(
            X["distance_to_facility_m"],
            5000,
        )

    return X.to_numpy()


# ============================================================
# TRAIN
# ============================================================

def train():

    os.makedirs(
        MODEL_DIR,
        exist_ok=True,
    )

    print("=" * 70)
    print(" PS162 — 5-Class Source Type ML Prototype")
    print("=" * 70)

    # --------------------------------------------------------
    # Load behavioral features
    # --------------------------------------------------------

    from features import load_behavioral_features

    features_df = load_behavioral_features()

    print(
        f"\n[ML] Feature rows: {len(features_df)}"
    )

    # --------------------------------------------------------
    # Load existing classifier labels
    # --------------------------------------------------------

    class_df = load_existing_classes()

    df = features_df.merge(
        class_df,
        on="hotspot_id",
        how="inner",
    )

    print(
        f"[ML] Rows after class join: {len(df)}"
    )

    # --------------------------------------------------------
    # Build weak labels
    # --------------------------------------------------------

    df = build_source_labels(df)

    print("\n[ML] Weak-label distribution:")

    print(
        df["source_type"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Remove classes with too few examples
    # --------------------------------------------------------

    counts = df["source_type"].value_counts()

    usable_classes = [
        cls
        for cls, count in counts.items()
        if count >= 10
    ]

    df = df[
        df["source_type"].isin(
            usable_classes
        )
    ].copy()

    print("\n[ML] Classes used for training:")

    print(
        df["source_type"]
        .value_counts()
        .to_string()
    )

    if len(usable_classes) < 3:

        raise RuntimeError(
            "Not enough source classes have at least "
            "10 observations for a multiclass prototype."
        )

    # --------------------------------------------------------
    # Encode labels
    # --------------------------------------------------------

    class_names = sorted(
        df["source_type"].unique()
    )

    class_to_id = {
        name: idx
        for idx, name in enumerate(class_names)
    }

    y = (
        df["source_type"]
        .map(class_to_id)
        .astype(int)
        .to_numpy()
    )

    X = build_X(df)

    print(
        f"\n[ML] Training matrix: {X.shape}"
    )

    print(
        f"[ML] Classes: {class_names}"
    )

    # --------------------------------------------------------
    # Spatial grouping
    # --------------------------------------------------------

    groups = (
        df["latitude"].round(1).astype(str)
        + "_"
        + df["longitude"].round(1).astype(str)
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="multi:softprob",
        num_class=len(class_names),
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    # --------------------------------------------------------
    # Cross-validation
    # --------------------------------------------------------

    min_class_count = (
        df["source_type"]
        .value_counts()
        .min()
    )

    n_splits = min(
        3,
        int(min_class_count),
    )

    print(
        f"\n[ML] Spatial cross-validation: "
        f"{n_splits} folds"
    )

    fold_results = []

    if n_splits >= 2:

        sgkf = StratifiedGroupKFold(
            n_splits=n_splits,
            shuffle=True,
            random_state=42,
        )

        for fold, (
            train_idx,
            val_idx,
        ) in enumerate(
            sgkf.split(X, y, groups),
            start=1,
        ):

            fold_model = XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                objective="multi:softprob",
                num_class=len(class_names),
                eval_metric="mlogloss",
                random_state=42,
                n_jobs=-1,
            )

            fold_model.fit(
                X[train_idx],
                y[train_idx],
                eval_set=[
                    (X[val_idx], y[val_idx])
                ],
                verbose=False,
            )

            predictions = (
                fold_model.predict(
                    X[val_idx]
                )
            )

            accuracy = (
                predictions == y[val_idx]
            ).mean()

            fold_results.append(
                {
                    "fold": fold,
                    "accuracy": float(
                        accuracy
                    ),
                }
            )

            print(
                f"  Fold {fold}: "
                f"accuracy={accuracy:.3f}"
            )

    # --------------------------------------------------------
    # Final model
    # --------------------------------------------------------

    print(
        "\n[ML] Training final model..."
    )

    model.fit(
        X,
        y,
        verbose=False,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    joblib.dump(
        model,
        MODEL_PATH,
    )

    metadata = {
        "model_type": (
            "XGBoost multiclass classifier"
        ),
        "task": "source_type_classification",
        "classes": class_names,
        "class_to_id": class_to_id,
        "feature_names": TRAIN_FEATURES,
        "feature_count": len(
            TRAIN_FEATURES
        ),
        "weak_supervision": True,
        "training_rows": int(len(df)),
        "cross_validation": fold_results,
    }

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    predictions = model.predict(X)

    print("\n" + "=" * 70)
    print(" FINAL MULTICLASS REPORT")
    print("=" * 70)

    print(
        classification_report(
            y,
            predictions,
            target_names=class_names,
        )
    )

    print("Confusion matrix:")

    print(
        confusion_matrix(
            y,
            predictions,
        )
    )

    print("\nTop feature importances:")

    importance = sorted(
        zip(
            TRAIN_FEATURES,
            model.feature_importances_,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    for name, value in importance[:12]:

        print(
            f"  {name:<35}"
            f"{value:.4f}"
        )

    print("\n" + "=" * 70)

    print(
        f"[ML] Model saved → {MODEL_PATH}"
    )

    print(
        f"[ML] Metadata saved → {METADATA_PATH}"
    )

    print(
        "[ML] Existing models were NOT modified."
    )

    print("=" * 70)


if __name__ == "__main__":
    train()