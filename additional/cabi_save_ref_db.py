import sqlite3
import os
import http.client
import json
import platform
from datetime import datetime

windows_path = [os.sep, 'Users','John','Documents','Share_VirtualBox',]
linux_path = [os.sep, 'media','sf_Share_VirtualBox',]

if (platform.system() == 'Linux'):
    src_path = linux_path.copy()
    dst_path = linux_path.copy()
else:
    src_path = windows_path.copy()
    dst_path = windows_path.copy()

src_path.append('db.sqlite3')
dst_path.append('cabi_ref.sqlite3')
src_sqlite_file = os.path.join(*src_path)
dst_sqlite_file = os.path.join(*dst_path)
                               

def create_dst_table():
    # Connecting to the database file
    conn = sqlite3.connect(dst_sqlite_file)
    c = conn.cursor()

    # Create a new SQLite table for existing stations
    create_stmt = """CREATE TABLE IF NOT EXISTS ref_stations
    (id integer PRIMARY KEY, name text, max_total integer,
    jurisdiction text, elevation float, lat float, lon float)"""
    c.execute(create_stmt)

    # Committing changes and closing the connection to the database file
    conn.commit()
    conn.close()

def get_stations():
    connection = http.client.HTTPSConnection('secure.capitalbikeshare.com')

    connection.request('GET', 'data/stations.json')
    response = connection.getresponse()
    data = response.read().decode('utf-8')
    response_obj = json.loads(data)
    station_ary = response_obj['stations']
    print(len(station_ary))
    timestamp = int(response_obj['timestamp'])/1000
    poll_dt = datetime.fromtimestamp(timestamp)
    poll_time = poll_dt.strftime('%Y-%m-%d %H:%M:%S')
    print(poll_time)
    return station_ary

def create_station_dict(station):
    """Extract/transform attributes from original dict loaded from json"""
    st_dict = {}
    st_dict['id'] = station['n']
    st_dict['name'] = station['s']
    # jurisdiction is taken from string formatted as
    # Reporting-Arlington, VA
    # so the initial part of 10 chars is dropped
    locality = station['d'][10:] 
    st_dict['jurisdiction'] = locality
    st_dict['lat'] = station['la']
    st_dict['lon'] = station['lo']
    return st_dict

def insert_station(conn, st_dict):
    cursor = conn.cursor()

    delete_stmt = "DELETE FROM ref_stations WHERE id=?"
    cursor.execute(delete_stmt, (st_dict['id'],))
    
    values = (st_dict['id'], st_dict['name'], st_dict['jurisdiction'],
              st_dict['lat'], st_dict['lon'])
    insert_stmt = """INSERT INTO ref_stations
    (id, name, jurisdiction, lat, lon)
    VALUES (?, ?, ?, ?, ?)"""
    cursor.execute(insert_stmt, values)

def update_stations(dconn):
    sconn = sqlite3.connect(src_sqlite_file)

    sc = sconn.cursor()
    select_stmt = """SELECT max_total, id FROM stations"""
    sc.execute(select_stmt)

    rows = sc.fetchall()
    sc.close()
    sconn.close()

    dc = dconn.cursor()
    update_stmt = "UPDATE ref_stations SET max_total=? WHERE id=?"""
    for row in rows:
        dc.execute(update_stmt, tuple(row))
    
    dconn.commit()
    dconn.close()

def process_stations():
    dconn = sqlite3.connect(dst_sqlite_file)
    stations = get_stations()
    for station in stations:
        st_dict = create_station_dict(station)
        insert_station(dconn, st_dict)
    update_stations(dconn)
    
if __name__ == "__main__":
    create_dst_table()
    process_stations()
    
    
