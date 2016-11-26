import sqlite3
import os
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

src_path.append('cabi_ref.sqlite3')
dst_path.append('db.sqlite3')
src_sqlite_file = os.path.join(*src_path)
dst_sqlite_file = os.path.join(*dst_path)

def get_stations():
    conn = sqlite3.connect(src_sqlite_file)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    select_stmt = """SELECT * FROM ref_stations ORDER BY id"""
    c.execute(select_stmt)
    rows = c.fetchall()
    
    c.close()
    conn.close()

    station_ary = []
    for row in rows:
        st_dict = create_station_dict(row)
        station_ary.append(st_dict)
    return station_ary

def create_station_dict(row):
    """Extract/transform attributes from original dict loaded from json"""
    st_dict = {}
    st_dict['id'] = row['id']
    st_dict['name'] = row['name']
    st_dict['jurisdiction'] = row['jurisdiction']
    st_dict['elevation'] = row['elevation']
    st_dict['lat'] = row['lat']
    st_dict['lon'] = row['lon']
    st_dict['max_total'] = row['max_total']
    return st_dict

def process_station(conn, st_dict):
    cursor = conn.cursor()

    delete_stmt = "DELETE FROM ref_stations WHERE id=?"
    cursor.execute(delete_stmt, (st_dict['id'],))
    
    values = (st_dict['id'], st_dict['name'], st_dict['max_total'],
              st_dict['jurisdiction'], st_dict['elevation'],
              st_dict['lat'], st_dict['lon'])
    insert_stmt = """INSERT INTO ref_stations
    (id, name, max_total, jurisdiction, elevation, lat, lon)
    VALUES (?, ?, ?, ?, ?, ?, ?)"""
    cursor.execute(insert_stmt, values)

    update_stmt = "UPDATE stations SET max_total=? WHERE id=?"""
    values = (st_dict['max_total'], st_dict['id'])
    cursor.execute(update_stmt, values)

def process_stations():
    stations = get_stations()

    dconn = sqlite3.connect(dst_sqlite_file)
    for station in stations:
        st_dict = create_station_dict(station)
        process_station(dconn, st_dict)

    dconn.commit()
    dconn.close()
    
if __name__ == "__main__":
    process_stations()

    
    
    
