"""
PS162 — New Behavioral ML Trainer

Purpose:
    Train a separate binary classifier:

        ANTHROPOGENIC / INDUSTRIAL
        vs
        NON-INDUSTRIAL / NATURAL

Safety:
    - Does NOT modify backend/ml/
    - Does NOT modify PostgreSQL
    - Does NOT overwrite existing model.pkl
    - Saves only into ml/models/
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from xgboost import XGBClassifier

from features import load_behavioral_features, build_feature_matrix, FEATURE_NAMES


MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "models",
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "anthropogenic_model.pkl",
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "anthropogenic_metadata.json",
)


# ============================================================
# FEATURE SUBSET
# ============================================================

# We deliberately exclude:
# - NDVI
# - NDBI
# - NDWI
#
# They are currently constant zero in the database.
#
# We also keep the feature interface compatible with
# the complete 32-feature extractor.

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


# ============================================================
# WEAK LABEL GENERATION
# ============================================================

def assign_weak_labels(df):
    """
    Create provisional labels from multiple independent signals.

    This is NOT ground truth.
    These labels are explicitly weak supervision.
    """

    labels = []
    scores = []

    for _, row in df.iterrows():

        score = 0
        evidence = []

        # ----------------------------------------------------
        # 1. Industrial land-use
        # ----------------------------------------------------

        if row["landuse_industrial"] == 1:
            score += 4
            evidence.append("industrial_landuse")

        # ----------------------------------------------------
        # 2. Facility proximity
        # ----------------------------------------------------

        distance = row["distance_to_facility_m"]

        if distance < 500:
            score += 4
            evidence.append("facility_<500m")

        elif distance < 1000:
            score += 2
            evidence.append("facility_<1km")

        # ----------------------------------------------------
        # 3. Persistent facility activity
        # ----------------------------------------------------

        if row["active_days_facility"] >= 10:
            score += 3
            evidence.append("persistent_facility")

        elif row["active_days_facility"] >= 3:
            score += 1
            evidence.append("repeated_facility")

        # ----------------------------------------------------
        # 4. FRP intensity
        # ----------------------------------------------------

        frp = row["frp"]

        if frp >= 50:
            score += 3
            evidence.append("high_frp")

        elif frp >= 25:
            score += 1
            evidence.append("moderate_frp")

        # ----------------------------------------------------
        # 5. Facility FRP behavior
        # ----------------------------------------------------

        if row["frp_vs_facility_avg"] >= 1.5:
            score += 1
            evidence.append("frp_above_facility_baseline")

        # ----------------------------------------------------
        # 6. Nighttime activity
        # ----------------------------------------------------

        if row["nighttime_fraction_facility"] >= 0.60:
            score += 2
            evidence.append("nighttime_facility_activity")

        # ----------------------------------------------------
        # 7. Agricultural context
        # ----------------------------------------------------

        if row["landuse_agricultural"] == 1:
            score -= 2
            evidence.append("agricultural_landuse")

        # Strong stubble-season agricultural signal
        if (
            row["landuse_agricultural"] == 1
            and row["is_stubble_season"] == 1
            and frp < 25
        ):
            score -= 3
            evidence.append("seasonal_low_frp_agriculture")

        # ----------------------------------------------------
        # Label
        # ----------------------------------------------------

        if score >= 4:
            label = "anthropogenic"
        elif score <= -2:
            label = "non_industrial"
        else:
            # Ambiguous samples are not forced into a class.
            label = "uncertain"

        labels.append(label)
        scores.append(score)

    df = df.copy()

    df["weak_label"] = labels
    df["weak_score"] = scores

    return df


# ============================================================
# REMOVE UNCERTAIN LABELS
# ============================================================

def prepare_training_data(df):

    df = assign_weak_labels(df)

    print("\n[ML] Weak-label distribution BEFORE filtering:")
    print(
        df["weak_label"]
        .value_counts()
        .to_string()
    )

    train_df = df[
        df["weak_label"].isin(
            ["anthropogenic", "non_industrial"]
        )
    ].copy()

    print(
        f"\n[ML] Training rows after removing "
        f"uncertain samples: {len(train_df)}"
    )

    print("\n[ML] Final label distribution:")
    print(
        train_df["weak_label"]
        .value_counts()
        .to_string()
    )

    return train_df


# ============================================================
# BUILD TRAINING MATRIX
# ============================================================

def build_X(df):

    missing = [
        feature
        for feature in TRAIN_FEATURES
        if feature not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Missing training features: {missing}"
        )

    X = (
        df[TRAIN_FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .astype(np.float32)
    )

    # Prevent sentinel distance 99999 from behaving
    # like a meaningful huge physical distance.
    if "distance_to_facility_m" in X.columns:
        X["distance_to_facility_m"] = np.minimum(
            X["distance_to_facility_m"],
            5000
        )

    return X.to_numpy()


# ============================================================
# TRAIN
# ============================================================

def train():

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    print("=" * 70)
    print(" PS162 — Anthropogenic Source ML Trainer")
    print("=" * 70)

    # --------------------------------------------------------
    # Load existing read-only feature dataset
    # --------------------------------------------------------

    df = load_behavioral_features()

    print(
        f"\n[ML] Loaded {len(df)} observations."
    )

    # --------------------------------------------------------
    # Weak labels
    # --------------------------------------------------------

    df = prepare_training_data(df)

    if len(df) < 100:
        raise RuntimeError(
            "Not enough labeled observations to train."
        )

    # --------------------------------------------------------
    # Encode target
    # --------------------------------------------------------

    label_map = {
        "non_industrial": 0,
        "anthropogenic": 1,
    }

    y = (
        df["weak_label"]
        .map(label_map)
        .astype(int)
        .to_numpy()
    )

    X = build_X(df)

    # --------------------------------------------------------
    # Spatial groups
    # --------------------------------------------------------

    groups = (
        df["latitude"].round(1).astype(str)
        + "_"
        + df["longitude"].round(1).astype(str)
    )

    print(
        f"\n[ML] Training matrix: {X.shape}"
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
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    # --------------------------------------------------------
    # Spatial cross-validation
    # --------------------------------------------------------

    n_splits = 3

    sgkf = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=42,
    )

    fold_results = []

    print("\n[ML] Spatial cross-validation:")

    for fold, (train_idx, val_idx) in enumerate(
        sgkf.split(X, y, groups),
        start=1,
    ):

        fold_model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
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

        probabilities = fold_model.predict_proba(
            X[val_idx]
        )[:, 1]

        predictions = (
            probabilities >= 0.5
        ).astype(int)

        accuracy = (
            predictions == y[val_idx]
        ).mean()

        try:
            auc = roc_auc_score(
                y[val_idx],
                probabilities,
            )
        except ValueError:
            auc = float("nan")

        fold_results.append(
            {
                "fold": fold,
                "accuracy": float(accuracy),
                "roc_auc": float(auc),
            }
        )

        print(
            f"  Fold {fold}: "
            f"accuracy={accuracy:.3f}, "
            f"ROC-AUC={auc:.3f}"
        )

    # --------------------------------------------------------
    # Final model on all labeled data
    # --------------------------------------------------------

    print("\n[ML] Training final model...")

    model.fit(
        X,
        y,
        verbose=False,
    )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    joblib.dump(
        model,
        MODEL_PATH,
    )

    metadata = {
        "model_type": "XGBoost binary classifier",
        "task": "anthropogenic_vs_non_industrial",
        "label_map": label_map,
        "feature_names": TRAIN_FEATURES,
        "feature_count": len(TRAIN_FEATURES),
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
    # Training report
    # --------------------------------------------------------

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)[:, 1]

    print("\n" + "=" * 70)
    print(" FINAL TRAINING REPORT")
    print("=" * 70)

    print(
        classification_report(
            y,
            predictions,
            target_names=[
                "non_industrial",
                "anthropogenic",
            ],
        )
    )

    try:
        print(
            f"ROC-AUC: "
            f"{roc_auc_score(y, probabilities):.4f}"
        )
    except ValueError:
        pass

    print("Confusion matrix:")
    print(
        confusion_matrix(
            y,
            predictions,
        )
    )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    importance = sorted(
        zip(
            TRAIN_FEATURES,
            model.feature_importances_,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    print("\nTop feature importances:")

    for name, value in importance[:12]:
        print(
            f"  {name:<35} "
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
        "[ML] Existing backend/ml model was NOT modified."
    )
    print("=" * 70)


if __name__ == "__main__":
    train()