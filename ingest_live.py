import psycopg2
import csv
from datetime import datetime

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="firedb",
    user="fireuser",
    password="firepass"
)
cur = conn.cursor()

with open('live_firms.csv') as f:
    reader = csv.DictReader(f)
    inserted = 0
    for row in reader:
        try:
            lat = float(row['latitude'])
            lon = float(row['longitude'])
            brightness = float(row.get('bright_ti4') or 0)
            frp = float(row.get('frp') or 0)
            confidence = row.get('confidence', 'n')
            acq_date = row.get('acq_date', str(datetime.today().date()))
            acq_time = row.get('acq_time', '0000')
            satellite = row.get('satellite', 'N')
            daynight = (row.get('daynight', 'D') or 'D')[:1]
            
            cur.execute(
                "INSERT INTO raw_hotspots (geom, latitude, longitude, brightness, frp, confidence, acq_date, acq_time, satellite, instrument, daynight) VALUES (ST_SetSRID(ST_MakePoint(%s,%s),4326), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (lon, lat, lat, lon, brightness, frp, confidence, acq_date, acq_time, satellite, 'VIIRS', daynight)
            )
            inserted += 1
        except Exception as e:
            print(f"Error on row: {e}")
            continue

conn.commit()
cur.close()
conn.close()
print(f"? Inserted {inserted} live FIRMS hotspots")
