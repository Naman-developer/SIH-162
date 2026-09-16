"""
Module 5 — Industrial Fire Classifier
Weak-label → XGBoost → writes predictions to classified_hotspots.
"""

import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import urllib.parse as up
import pandas as pd
import numpy as np
import joblib
from collections import Counter
from dotenv import load_dotenv
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

load_dotenv()
DB_URL       = os.getenv("DATABASE_URL", "postgresql://fireuser:firepass@localhost:5432/firedb")
MODEL_PATH   = os.path.join(os.path.dirname(__file__), "model.pkl")
ENCODER_PATH = os.path.join(os.path.dirname(__file__), "label_encoder.pkl")


def get_conn():
    r = up.urlparse(DB_URL)
    return psycopg2.connect(
        host=r.hostname, port=r.port or 5432,
        dbname=r.path.lstrip("/"),
        user=r.username, password=r.password,
    )


# ── 1. Load features ──────────────────────────────────────────────────────────

def load_features():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT
            r.id                                  AS hotspot_id,
            r.latitude,
            r.longitude,
            COALESCE(r.brightness, 300)           AS brightness,
            COALESCE(r.frp, 0)                    AS frp,
            CASE r.confidence
                WHEN 'high'   THEN 3
                WHEN 'h'      THEN 3
                WHEN 'medium' THEN 2
                WHEN 'n'      THEN 2
                ELSE 1
            END                                   AS confidence_num,
            CASE r.daynight WHEN 'D' THEN 1 ELSE 0 END AS is_day,
            COALESCE(EXTRACT(HOUR  FROM r.acq_datetime), 12) AS hour_of_day,
            COALESCE(EXTRACT(MONTH FROM r.acq_datetime), 10) AS month,
            CASE WHEN EXTRACT(MONTH FROM r.acq_datetime) IN (10, 11)
                 THEN 1 ELSE 0 END                AS is_stubble_season,
            COALESCE(e.distance_m, 99999)         AS distance_to_facility_m,
            COALESCE(e.neighbor_count_1km_24h, 0) AS neighbor_count,
            COALESCE(e.landuse_class, 'unknown')  AS landuse_class
        FROM raw_hotspots r
        LEFT JOIN enriched_hotspots e ON e.raw_hotspot_id = r.id
        WHERE r.acq_datetime IS NOT NULL
    """, conn)
    conn.close()
    print(f"[ML] Loaded {len(df)} rows.")
    return df


# ── 2. Weak labels ────────────────────────────────────────────────────────────

def assign_weak_labels(df):
    labels = []
    for _, row in df.iterrows():
        dist = row["distance_to_facility_m"]
        lc   = row["landuse_class"]
        mon  = int(row["month"])
        frp  = row["frp"]

        if dist < 500 or lc == "industrial":
            labels.append("industrial")
        elif lc == "forest":
            labels.append("forest")
        elif lc == "farmland":
            labels.append("agricultural")
        elif frp > 40 and dist < 2000:
            labels.append("industrial")
        elif mon in (10, 11) and frp < 20:
            labels.append("agricultural")
        else:
            labels.append("other")

    df["weak_label"] = labels
    print("\n[ML] Weak label distribution:")
    print(df["weak_label"].value_counts().to_string())
    return df


# ── 3. Feature matrix ─────────────────────────────────────────────────────────

FEATURE_COLS    = [
    "brightness", "frp", "confidence_num", "is_day",
    "hour_of_day", "month", "is_stubble_season",
    "distance_to_facility_m", "neighbor_count",
]
LANDUSE_CLASSES = ["industrial", "farmland", "forest", "urban", "unknown"]


def build_X(df):
    X = df[FEATURE_COLS].copy()
    for lc in LANDUSE_CLASSES:
        X[f"lc_{lc}"] = (df["landuse_class"] == lc).astype(int)
    return X.values.astype(np.float32)


# ── 4. Train ──────────────────────────────────────────────────────────────────

def train():
    df  = load_features()
    df  = assign_weak_labels(df)
    le  = LabelEncoder()
    y   = le.fit_transform(df["weak_label"])
    X   = build_X(df)

    groups = (df["latitude"].round(1).astype(str) + "_" +
              df["longitude"].round(1).astype(str))

    print(f"\n[ML] Training XGBoost — {len(X)} samples, classes: {list(le.classes_)}")

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    sgkf = StratifiedGroupKFold(n_splits=3)
    for fold, (tr_idx, val_idx) in enumerate(sgkf.split(X, y, groups)):
        model.fit(X[tr_idx], y[tr_idx],
                  eval_set=[(X[val_idx], y[val_idx])], verbose=False)
        acc = (model.predict(X[val_idx]) == y[val_idx]).mean()
        print(f"     Fold {fold+1} accuracy: {acc:.3f}")

    # Final fit on all data
    model.fit(X, y, verbose=False)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(le,    ENCODER_PATH)
    print(f"\n[ML] Model saved → {MODEL_PATH}")

    # Full report
    preds = model.predict(X)
    print("\n── Classification Report ──")
    print(classification_report(y, preds, target_names=le.classes_))

    # Feature importances
    feat_names = FEATURE_COLS + [f"lc_{lc}" for lc in LANDUSE_CLASSES]
    importances = sorted(zip(feat_names, model.feature_importances_),
                         key=lambda x: x[1], reverse=True)
    print("── Top Feature Importances ──")
    for name, imp in importances[:8]:
        print(f"  {name:<30} {imp:.4f}  {'█' * int(imp * 50)}")

    return model, le


# ── 5. Inference → DB ─────────────────────────────────────────────────────────

def run_inference():
    if not os.path.exists(MODEL_PATH):
        print("[ML] No model found — training first.")
        train()

    model = joblib.load(MODEL_PATH)
    le    = joblib.load(ENCODER_PATH)
    df    = load_features()
    X     = build_X(df)

    probs   = model.predict_proba(X)
    classes = le.inverse_transform(model.predict(X))
    conf    = probs.max(axis=1)

    conn = get_conn()
    cur  = conn.cursor()

    cur.execute("SELECT raw_hotspot_id, id FROM enriched_hotspots")
    enriched_map = {row[0]: row[1] for row in cur.fetchall()}

    sql = """
        INSERT INTO classified_hotspots
            (enriched_id, geom, predicted_class, confidence_score, class_probs, classified_at)
        SELECT %s, geom, %s, %s, %s::jsonb, NOW()
        FROM enriched_hotspots WHERE id = %s
        ON CONFLICT (enriched_id) DO UPDATE SET
            predicted_class  = EXCLUDED.predicted_class,
            confidence_score = EXCLUDED.confidence_score,
            class_probs      = EXCLUDED.class_probs,
            classified_at    = NOW()
    """

    inserted = 0
    skipped  = 0
    for idx in range(len(df)):
        row = df.iloc[idx]
        eid = enriched_map.get(int(row["hotspot_id"]))
        if eid is None:
            skipped += 1
            continue
        prob_dict = {cls: round(float(p), 4)
                     for cls, p in zip(le.classes_, probs[idx])}
        cur.execute(sql, (
            eid,
            classes[idx],
            round(float(conf[idx]), 4),
            json.dumps(prob_dict),
            eid,
        ))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n[ML] ✓ {inserted} predictions written  ({skipped} skipped).")

    print("\n── Predicted Class Breakdown ──")
    for cls, cnt in sorted(Counter(classes).items(), key=lambda x: -x[1]):
        pct = cnt / len(classes) * 100
        print(f"  {cls:<15} {cnt:>5}  ({pct:.1f}%)  {'█' * int(pct / 2)}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  PS162 — Module 5: ML Classifier")
    print("=" * 60)
    train()
    run_inference()
    print("\n[DONE] Module 5 complete. Ready for Module 6 — FastAPI.")