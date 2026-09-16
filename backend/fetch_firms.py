"""
Module 2 — FIRMS Ingestion
Pulls real VIIRS hotspot data for Punjab/Haryana bbox and loads into raw_hotspots.
Synthetic fallback: 90 days, Oct-Nov agricultural peak, ~2000 rows.
"""

import os
import csv
import io
import math
import random
import requests
import psycopg2
import json
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("FIRMS_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "FIRMS_API_KEY is not set. Configure it in Docker/.env."
    )

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fireuser:firepass@localhost:5432/firedb"
)
BBOX = "73.8,29.5,77.5,32.0"

SOURCES = [
    ("VIIRS_NOAA21_NRT", 5),
    ("VIIRS_NOAA20_NRT", 5),
    ("VIIRS_SNPP_NRT", 5),
]
STATUS_FILE = Path(__file__).resolve().parent / "data_status.json"  

def write_status(mode, source, rows, message=""):
    STATUS_FILE.write_text(
        json.dumps(
            {
                "mode": mode,
                "source": source,
                "rows": rows,
                "message": message,
                "updated_at": datetime.now(timezone.utc).isoformat()   
            },
            indent=2
        )
    )

# ── DB CONNECTION ─────────────────────────────────────────────────────────────
def get_conn():
    import urllib.parse as up
    r = up.urlparse(DB_URL)
    return psycopg2.connect(
        host=r.hostname, port=r.port or 5432,
        dbname=r.path.lstrip("/"),
        user=r.username, password=r.password,
    )

# ── FETCH FROM FIRMS API ──────────────────────────────────────────────────────
def fetch_firms_csv(source: str, days: int) -> list:
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{API_KEY}/{source}/{BBOX}/{days}"
    print(f"\n[FIRMS] Source={source} Days={days}")
    print(f"[FIRMS] Fetching {source} for {days} day(s)")
    try:
        resp = requests.get(url, timeout=60)
    except Exception as e:
        print(f"[FIRMS] Network error: {e}")
        return []
    if resp.status_code != 200:
        print(f"[FIRMS] HTTP {resp.status_code}: {resp.text[:200]}")
        return []
    content = resp.text.strip()
    if not content or "latitude" not in content.lower():
        print(f"[FIRMS] Empty response: {content[:100]}")
        return []
    rows = list(csv.DictReader(io.StringIO(content)))
    print(f"[FIRMS] Got {len(rows)} rows")
    return rows

# ── LOAD INTO DB ──────────────────────────────────────────────────────────────
def load_to_db(rows: list) -> int:
    if not rows:
        return 0
    conn = get_conn()
    cur  = conn.cursor()
    sql = """
        INSERT INTO raw_hotspots
            (geom, latitude, longitude, brightness, frp, confidence,
             acq_date, acq_time, satellite, instrument, daynight)
        VALUES (ST_SetSRID(ST_MakePoint(%s,%s),4326), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    inserted = skipped = 0
    for row in rows:
        try:
            lat  = float(row.get("latitude") or 0)
            lon  = float(row.get("longitude") or 0)
            brt  = float(row.get("bright_ti4") or row.get("brightness") or 0)
            frp  = float(row.get("frp") or 0)
            conf = str(row.get("confidence","")).strip().lower()
            date_str = row.get("acq_date","")
            time_str = str(row.get("acq_time","0000")).zfill(4)
            sat  = row.get("satellite","")
            inst = row.get("instrument","")
            dn   = row.get("daynight","")
            if not lat or not lon:
                skipped += 1; continue
            try:    acq_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except: acq_date = None
            cur.execute(sql, (lon,lat, lat,lon, brt,frp,conf, acq_date,time_str, sat,inst,dn))
            inserted += 1
        except Exception as e:
            skipped += 1
    conn.commit(); cur.close(); conn.close()
    print(f"[DB] Inserted={inserted} Skipped={skipped}")
    return inserted

# ── VERIFY ────────────────────────────────────────────────────────────────────
def verify():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM raw_hotspots;")
    total = cur.fetchone()[0]
    cur.execute("""
        SELECT acq_date, COUNT(*),
               ROUND(AVG(frp)::numeric,2),
               ROUND(AVG(brightness)::numeric,2)
        FROM raw_hotspots
        GROUP BY acq_date ORDER BY acq_date DESC LIMIT 15;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    print(f"\n{'='*58}")
    print(f"  TOTAL hotspots in DB: {total}")
    print(f"{'='*58}")
    print(f"  {'Date':<13} {'Count':>6}  {'Avg FRP':>8}  {'Avg Bright':>10}")
    print(f"  {'-'*48}")
    for r in rows:
        print(f"  {str(r[0]):<13} {r[1]:>6}  {str(r[2]):>8}  {str(r[3]):>10}")
    print(f"{'='*58}\n")

# ── SYNTHETIC DATA (90 days, Oct-Nov peak) ────────────────────────────────────
def load_synthetic_data():
    random.seed(42)

    # Start date: Aug 1 2026 → 90 days → Oct 29 2026
    START = date(2026, 8, 1)
    DAYS  = 90

    # Agricultural intensity curve:
    # Aug: low (0.1), Sep: medium (0.4), Oct: HIGH (1.0), Nov start: falling (0.7)
    def agri_intensity(day_offset):
        d = START + timedelta(days=day_offset)
        if d.month == 8:  return 0.10
        if d.month == 9:  return 0.40
        if d.month == 10: return 1.00   # peak stubble burning
        return 0.70

    # ── Industrial sites: persistent, year-round, high brightness ──
    industrial_sites = [
        (30.2069, 75.1240, "Bathinda Thermal",    45, 8),   # lat,lon,name,avg_frp,frp_std
        (29.9008, 76.1951, "Panipat Refinery",     38, 7),
        (30.9010, 75.8573, "Ludhiana Industrial",  32, 9),
        (29.1492, 75.7217, "Hisar Thermal",         28, 6),
        (29.3887, 76.9635, "Yamuna Nagar Mills",   22, 5),
    ]

    # ── Agricultural burning zones: large clusters, seasonal ──
    agri_zones = [
        (30.52, 74.30, 1.2),   # SW Punjab — heavy burning
        (31.10, 74.88, 0.9),   # Amritsar belt
        (30.85, 75.90, 1.0),   # Ludhiana farmland
        (29.70, 76.50, 0.8),   # Haryana farmland
        (31.40, 75.20, 0.6),   # Gurdaspur
        (30.30, 76.80, 0.7),   # Ambala belt
        (29.50, 74.80, 0.5),   # Sirsa district
    ]

    # ── Forest zones: sparse, low FRP ──
    forest_zones = [
        (31.50, 75.70, 0.3),   # Pathankot forests
        (30.65, 77.20, 0.2),   # Shivalik foothills
        (31.80, 75.40, 0.25),  # Hoshiarpur hilly
    ]

    rows = []

    # INDUSTRIAL — 90 days, 70% detection rate per day, slight anomaly spikes
    for lat, lon, name, avg_frp, frp_std in industrial_sites:
        for day in range(DAYS):
            if random.random() > 0.70:   # 70% chance detected each day
                continue
            acq_date = START + timedelta(days=day)
            # Anomaly spike: random 5% of days have 2x FRP
            spike = 2.2 if random.random() < 0.05 else 1.0
            frp   = max(1.0, random.gauss(avg_frp, frp_std) * spike)
            brt   = random.gauss(332, 6) + (frp - avg_frp) * 0.3
            rows.append({
                "lat": lat + random.gauss(0, 0.001),
                "lon": lon + random.gauss(0, 0.001),
                "brightness": round(brt, 2),
                "frp":        round(frp, 2),
                "confidence": "high",
                "acq_date":   acq_date,
                "acq_time":   f"{random.choice([2,3,4,5,14,15]):02d}30",
                "satellite":  "N",
                "instrument": "VIIRS",
                "daynight":   "N" if random.random() > 0.35 else "D",
            })

    # AGRICULTURAL — scaled by intensity curve, daytime only
    for clat, clon, radius in agri_zones:
        for day in range(DAYS):
            intensity = agri_intensity(day)
            # Base fires per day for this zone, scaled by intensity
            n_fires = int(random.gauss(18 * intensity, 4 * intensity + 1))
            n_fires = max(0, n_fires)
            for _ in range(n_fires):
                angle = random.uniform(0, 2 * math.pi)
                r     = random.uniform(0, radius) * math.sqrt(random.random())
                rows.append({
                    "lat": clat + r * math.sin(angle),
                    "lon": clon + r * math.cos(angle),
                    "brightness": random.gauss(308, 14),
                    "frp":        max(0.5, random.gauss(13, 5)),
                    "confidence": random.choices(
                        ["high","medium","low"], weights=[60,30,10])[0],
                    "acq_date":   START + timedelta(days=day),
                    "acq_time":   f"{random.randint(10,15):02d}00",
                    "satellite":  "N",
                    "instrument": "VIIRS",
                    "daynight":   "D",
                })

    # FOREST — sparse random events
    for clat, clon, radius in forest_zones:
        n = random.randint(8, 20)
        for _ in range(n):
            rows.append({
                "lat": clat + random.gauss(0, radius),
                "lon": clon + random.gauss(0, radius),
                "brightness": random.gauss(296, 7),
                "frp":        max(0.5, random.gauss(7, 3)),
                "confidence": random.choice(["medium","low"]),
                "acq_date":   START + timedelta(days=random.randint(0, DAYS-1)),
                "acq_time":   f"{random.randint(8,17):02d}00",
                "satellite":  "N",
                "instrument": "VIIRS",
                "daynight":   "D",
            })

    # ── Insert all rows ──
    conn = get_conn()
    cur  = conn.cursor()
    sql  = """
        INSERT INTO raw_hotspots
            (geom, latitude, longitude, brightness, frp, confidence,
             acq_date, acq_time, satellite, instrument, daynight)
        VALUES (ST_SetSRID(ST_MakePoint(%s,%s),4326),
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    for r in rows:
        cur.execute(sql, (
            r["lon"], r["lat"],
            r["lat"], r["lon"],
            r["brightness"], r["frp"], r["confidence"],
            r["acq_date"], r["acq_time"],
            r["satellite"], r["instrument"], r["daynight"],
        ))
    conn.commit(); cur.close(); conn.close()

    # Summary by month
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT
            TO_CHAR(acq_date,'Mon YYYY') as month,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE confidence='high') as high_conf
        FROM raw_hotspots
        GROUP BY TO_CHAR(acq_date,'Mon YYYY'), DATE_TRUNC('month',acq_date)
        ORDER BY DATE_TRUNC('month',acq_date);
    """)
    monthly = cur.fetchall()
    cur.close(); conn.close()

    print(f"\n[SYNTHETIC] Inserted {len(rows)} hotspots across 90 days")
    print(f"\n  {'Month':<12} {'Total':>7}  {'High Conf':>10}")
    print(f"  {'-'*34}")
    for m in monthly:
        print(f"  {m[0]:<12} {m[1]:>7}  {m[2]:>10}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  PS162 — Module 2: FIRMS Ingestion")
    print(f"  API Key : {API_KEY[:8]}...")
    print(f"  AOI     : Punjab + Haryana ({BBOX})")
    print("=" * 60)

    write_status(
        "LOADING",
        "NASA FIRMS",
        0,
        "Trying NASA FIRMS..."
    )

    total_inserted = 0
    live_source = None

    for source, days in SOURCES:
        rows = fetch_firms_csv(source, days)

        if rows:
            n = load_to_db(rows)

            if n > 0:
                total_inserted = n
                live_source = source

                write_status(
                    "LIVE",
                    source,
                    n,
                    "NASA FIRMS data loaded successfully"
                )

                print(
                    f"[LIVE] NASA FIRMS → {source} → {n} rows"
                )

                break

        print(
            f"[SKIP] {source} → no usable data, trying next..."
        )

    if total_inserted == 0:
        print("\n[DEMO] NASA FIRMS unavailable.")
        print("[DEMO] Loading 90-day synthetic dataset...\n")

        load_synthetic_data()

        write_status(
            "DEMO",
            "synthetic",
            0,
            "NASA FIRMS unavailable; synthetic fallback loaded"
        )

        print("[DEMO] Synthetic fallback loaded.")

    verify()

    print("=" * 60)
    print(
        f"[DONE] Module 2 complete — "
        f"{'LIVE' if live_source else 'DEMO'} mode"
    )
    print("=" * 60)