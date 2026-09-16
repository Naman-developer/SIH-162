CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

CREATE TABLE IF NOT EXISTS raw_hotspots (
    id              SERIAL PRIMARY KEY,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    latitude        FLOAT NOT NULL,
    longitude       FLOAT NOT NULL,
    brightness      FLOAT,
    frp             FLOAT,
    confidence      VARCHAR(10),
    acq_date        DATE,
    acq_time        VARCHAR(6),
    satellite       VARCHAR(10),
    instrument      VARCHAR(10),
    daynight        CHAR(1),
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_raw_hotspots_geom ON raw_hotspots USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_raw_hotspots_date ON raw_hotspots(acq_date);

CREATE TABLE IF NOT EXISTS osm_facilities (
    id              SERIAL PRIMARY KEY,
    geom            GEOMETRY(Point, 4326),
    osm_id          BIGINT,
    name            VARCHAR(255),
    facility_type   VARCHAR(100),
    industry        VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS idx_osm_facilities_geom ON osm_facilities USING GIST(geom);

CREATE TABLE IF NOT EXISTS landcover_zones (
    id              SERIAL PRIMARY KEY,
    geom            GEOMETRY(Geometry, 4326),
    landuse_class   VARCHAR(50),
    name            VARCHAR(255),
    source          VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_landcover_geom ON landcover_zones USING GIST(geom);

CREATE TABLE IF NOT EXISTS enriched_hotspots (
    id                      SERIAL PRIMARY KEY,
    raw_hotspot_id          INT REFERENCES raw_hotspots(id),
    geom                    GEOMETRY(Point, 4326),
    nearest_facility_id     INT REFERENCES osm_facilities(id),
    nearest_facility_name   VARCHAR(255),
    distance_m              FLOAT,
    landuse_class           VARCHAR(50),
    neighbor_count_1km_24h  INT DEFAULT 0,
    ndvi_value              FLOAT,
    ndbi_value              FLOAT,
    ndwi_value              FLOAT,
    enriched_at             TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_enriched_geom ON enriched_hotspots USING GIST(geom);

CREATE TABLE IF NOT EXISTS classified_hotspots (
    id                  SERIAL PRIMARY KEY,
    enriched_id         INT REFERENCES enriched_hotspots(id),
    geom                GEOMETRY(Point, 4326),
    predicted_class     VARCHAR(30),
    confidence_score    FLOAT,
    class_probs         JSONB,
    classified_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_classified_geom ON classified_hotspots USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_classified_class ON classified_hotspots(predicted_class);

CREATE TABLE IF NOT EXISTS persistent_sources (
    id              SERIAL PRIMARY KEY,
    geom            GEOMETRY(Point, 4326),
    cluster_label   INT,
    active_days     INT DEFAULT 0,
    first_seen      DATE,
    last_seen       DATE,
    avg_frp         FLOAT,
    max_frp         FLOAT,
    facility_name   VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_persistent_geom ON persistent_sources USING GIST(geom);

CREATE TABLE IF NOT EXISTS anomaly_flags (
    id                   SERIAL PRIMARY KEY,
    persistent_source_id INT REFERENCES persistent_sources(id),
    classified_id        INT REFERENCES classified_hotspots(id),
    geom                 GEOMETRY(Point, 4326),
    z_score              FLOAT,
    severity             VARCHAR(10),
    flagged_at           TIMESTAMP DEFAULT NOW(),
    reason               TEXT
);
CREATE INDEX IF NOT EXISTS idx_anomaly_geom ON anomaly_flags USING GIST(geom);

CREATE TABLE IF NOT EXISTS fire_events (
    id              SERIAL PRIMARY KEY,
    geom            GEOMETRY(Point, 4326),
    event_label     VARCHAR(50),
    member_count    INT DEFAULT 0,
    started_at      TIMESTAMP,
    ended_at        TIMESTAMP,
    dominant_class  VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS event_members (
    event_id        INT REFERENCES fire_events(id),
    classified_id   INT REFERENCES classified_hotspots(id),
    PRIMARY KEY (event_id, classified_id)
);

CREATE TABLE IF NOT EXISTS event_graph_edges (
    id              SERIAL PRIMARY KEY,
    from_id         INT REFERENCES classified_hotspots(id),
    to_id           INT REFERENCES classified_hotspots(id),
    distance_m      FLOAT,
    time_diff_hrs   FLOAT
);

INSERT INTO osm_facilities (geom, name, facility_type, industry) VALUES
  (ST_SetSRID(ST_MakePoint(76.1951, 29.9008), 4326), 'Panipat Refinery', 'refinery', 'petroleum'),
  (ST_SetSRID(ST_MakePoint(75.1240, 30.2069), 4326), 'Bathinda Thermal Power Plant', 'power_plant', 'thermal'),
  (ST_SetSRID(ST_MakePoint(75.8573, 30.9010), 4326), 'Ludhiana Industrial Zone', 'industrial_zone', 'manufacturing'),
  (ST_SetSRID(ST_MakePoint(74.8723, 31.6340), 4326), 'Amritsar Industrial Area', 'industrial_zone', 'manufacturing'),
  (ST_SetSRID(ST_MakePoint(76.7794, 30.7333), 4326), 'Chandigarh Industrial Area', 'industrial_zone', 'mixed'),
  (ST_SetSRID(ST_MakePoint(75.7217, 29.1492), 4326), 'Hisar Thermal Plant', 'power_plant', 'thermal'),
  (ST_SetSRID(ST_MakePoint(76.0856, 28.8929), 4326), 'Rohtak Industrial Zone', 'industrial_zone', 'manufacturing'),
  (ST_SetSRID(ST_MakePoint(74.4941, 31.5204), 4326), 'Tarn Taran Industrial', 'industrial_zone', 'agro-processing'),
  (ST_SetSRID(ST_MakePoint(75.3412, 30.6940), 4326), 'Jalandhar Industrial Area', 'industrial_zone', 'manufacturing'),
  (ST_SetSRID(ST_MakePoint(76.9635, 29.3887), 4326), 'Yamuna Nagar Paper Mills', 'mill', 'paper');