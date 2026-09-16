@app.post('/ingest-live')
def ingest_live():
    import requests, csv, io
    from datetime import date as dt
    API_KEY = os.getenv('FIRMS_API_KEY', '4fe852e29b12201748db57fce62a182b')
    url = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv/' + API_KEY + '/VIIRS_SNPP_NRT/73.8,29.5,77.5,32.0/2'
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return {'error': str(e)}
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        return {'inserted': 0}
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        try:
            lat = float(r['latitude'])
            lon = float(r['longitude'])
            frp = float(r.get('frp') or 0)
            brightness = float(r.get('bright_ti4') or 0)
            cur.execute('INSERT INTO raw_hotspots (geom,latitude,longitude,brightness,frp,confidence,acq_date,acq_time,satellite,instrument,daynight) VALUES (ST_SetSRID(ST_MakePoint(' + str(lon) + ',' + str(lat) + '),4326),' + str(lat) + ',' + str(lon) + ',' + str(brightness) + ',' + str(frp) + ',' + chr(39) + str(r.get('confidence','n')) + chr(39) + ',' + chr(39) + str(r.get('acq_date', str(dt.today()))) + chr(39) + ',' + chr(39) + str(r.get('acq_time','0000')) + chr(39) + ',' + chr(39) + str(r.get('satellite','N')) + chr(39) + ',' + chr(39) + 'VIIRS' + chr(39) + ',' + chr(39) + str(r.get('daynight','D'))[:1] + chr(39) + ') ON CONFLICT DO NOTHING')
            inserted += 1
        except:
            continue
    conn.commit()
    cur.close()
    conn.close()
    return {'inserted': inserted, 'total_rows': len(rows)}
