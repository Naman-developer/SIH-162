"""
Module 4 — Geospatial Context Engine
For each unenriched raw_hotspot, computes via PostGIS:
  1. Nearest OSM facility + distance (ST_DWithin LATERAL join)
  2. Land-use class at point         (ST_Contains)
  3. Neighbor hotspot count 1km/24h  (ST_DWithin + acq_datetime window)
Writes output → enriched_hotspots table.
"""

import os
import psycopg2
import urllib.parse as up
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://fireuser:firepass@localhost:5432/firedb")

def get_conn():
    r = up.urlparse(DB_URL)
    return psycopg2.connect(
        host=r.hostname, port=r.port or 5432,
        dbname=r.path.lstrip("/"),
        user=r.username, password=r.password,
    )


# ── Main enrichment ────────────────────────────────────────────────────────────

def enrich_hotspots(batch_size: int = 300):
    conn = get_conn()
    cur  = conn.cursor()

    # Count unenriched
    cur.execute("""
        SELECT COUNT(*) FROM raw_hotspots r
        WHERE NOT EXISTS (
            SELECT 1 FROM enriched_hotspots e WHERE e.raw_hotspot_id = r.id
        )
    """)
    total = cur.fetchone()[0]

    if total == 0:
        print("[ENRICH] Nothing to enrich — all hotspots already processed.")
        cur.close(); conn.close()
        return 0

    print(f"[ENRICH] {total} hotspots to enrich, batch_size={batch_size}...")
    processed = 0

    while True:
        # Fetch next batch of unenriched IDs
        cur.execute("""
            SELECT r.id FROM raw_hotspots r
            WHERE NOT EXISTS (
                SELECT 1 FROM enriched_hotspots e WHERE e.raw_hotspot_id = r.id
            )
            ORDER BY r.id
            LIMIT %s
        """, (batch_size,))
        batch_ids = [row[0] for row in cur.fetchall()]
        if not batch_ids:
            break

        # Core enrichment SQL — one INSERT per batch using PostGIS
        cur.execute("""
            INSERT INTO enriched_hotspots
                (raw_hotspot_id, geom,
                 nearest_facility_id, nearest_facility_name, distance_m,
                 landuse_class,
                 neighbor_count_1km_24h)

            SELECT
                r.id,
                r.geom,

                -- 1. Nearest OSM facility within 10km (LATERAL)
                fac.id,
                fac.name,
                ROUND(ST_Distance(r.geom::geography, fac.geom::geography)::numeric, 1),

                -- 2. Landuse at point (ST_Contains)
                COALESCE(lz.landuse_class, 'unknown'),

                -- 3. Neighbor count 1km / 24h
                COALESCE(nc.cnt, 0)

            FROM raw_hotspots r

            LEFT JOIN LATERAL (
                SELECT id, name, geom
                FROM osm_facilities
                WHERE ST_DWithin(r.geom::geography, geom::geography, 10000)
                ORDER BY r.geom::geography <-> geom::geography
                LIMIT 1
            ) fac ON TRUE

            LEFT JOIN LATERAL (
                SELECT landuse_class
                FROM landcover_zones
                WHERE ST_Contains(geom, r.geom)
                LIMIT 1
            ) lz ON TRUE

            LEFT JOIN LATERAL (
                SELECT COUNT(*)::int AS cnt
                FROM raw_hotspots r2
                WHERE r2.id != r.id
                  AND ST_DWithin(r.geom::geography, r2.geom::geography, 1000)
                  AND r.acq_datetime IS NOT NULL
                  AND r2.acq_datetime IS NOT NULL
                  AND ABS(EXTRACT(EPOCH FROM (r.acq_datetime - r2.acq_datetime))) <= 86400
            ) nc ON TRUE

            WHERE r.id = ANY(%s)

            ON CONFLICT (raw_hotspot_id) DO UPDATE SET
                nearest_facility_id    = EXCLUDED.nearest_facility_id,
                nearest_facility_name  = EXCLUDED.nearest_facility_name,
                distance_m             = EXCLUDED.distance_m,
                landuse_class          = EXCLUDED.landuse_class,
                neighbor_count_1km_24h = EXCLUDED.neighbor_count_1km_24h,
                enriched_at            = NOW()
        """, (batch_ids,))


        conn.commit()
        processed += len(batch_ids)
        pct = int(processed / total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r  [{bar}] {processed}/{total} ({pct}%)", end="", flush=True)

    print(f"\n[ENRICH] ✓ Done. {processed} rows written to enriched_hotspots.")
    cur.close(); conn.close()
    return processed


# ── Verify ─────────────────────────────────────────────────────────────────────

def verify_enrichment():
    conn = get_conn()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM enriched_hotspots")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT
            landuse_class,
            COUNT(*)                                AS count,
            ROUND(AVG(distance_m)::numeric, 0)     AS avg_dist_m,
            ROUND(AVG(neighbor_count_1km_24h)::numeric, 2) AS avg_neighbors
        FROM enriched_hotspots
        GROUP BY landuse_class
        ORDER BY count DESC
    """)
    rows = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM enriched_hotspots WHERE distance_m < 500")
    near = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_hotspots WHERE neighbor_count_1km_24h > 5")
    dense = cur.fetchone()[0]

    print(f"\n{'='*65}")
    print(f"  enriched_hotspots — Context Summary   (total: {total})")
    print(f"{'='*65}")
    print(f"  {'Landuse Class':<18} {'Count':>7}  {'Avg Dist(m)':>11}  {'Avg Neighbors':>13}")
    print(f"  {'-'*58}")
    for r in rows:
        lc = (r[0] or "unknown")
        print(f"  {lc:<18} {r[1]:>7}  {str(r[2]):>11}  {str(r[3]):>13}")
    print(f"{'='*65}")
    print(f"  Within 500m of a facility : {near}")
    print(f"  Dense clusters (>5 nbrs)  : {dense}")
    print(f"{'='*65}\n")

    cur.close(); conn.close()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  PS162 — Module 4: Geospatial Context Engine")
    print("=" * 60)
    enrich_hotspots()
    verify_enrichment()
    print("[DONE] Module 4 complete. Ready for Module 5 — ML Classifier.")