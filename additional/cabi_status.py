import http.client
import json
import sqlite3
import sys
import os
import platform
from datetime import datetime
import pytz

def get_stations():
    connection = http.client.HTTPSConnection('secure.capitalbikeshare.com')

    connection.request('GET', 'data/stations.json')
    response = connection.getresponse()
    data = response.read().decode('utf-8')
    response_obj = json.loads(data)
    station_ary = response_obj['stations']
    print(len(station_ary))
    timestamp = int(response_obj['timestamp']/1000)
    print(timestamp)
    poll_dt = datetime.utcfromtimestamp(timestamp)
    utc_tz = pytz.timezone('UTC')
    est_tz = pytz.timezone('US/Eastern')
    est_dt = utc_tz.localize(poll_dt).astimezone(est_tz)
    est_dt = est_tz.normalize(est_dt)
    poll_time = est_dt.strftime('%Y-%m-%d %H:%M:%S')
    print(poll_time)
    return station_ary, timestamp

def print_station(station):
    print(station)

def create_station_insert_params(st_dict):
    return (st_dict['id'], st_dict['name'], st_dict['poll_time'],
            st_dict['total'], st_dict['max_total'],
            st_dict['bikes'], st_dict['docks'],
            st_dict['lc'], st_dict['lu'])

def insert_station(conn, values):
    insert_stmt = """INSERT INTO stations
    (id, name, poll_time, curr_total, max_total, bikes, docks, lc, lu)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    cursor = conn.cursor()
    cursor.execute(insert_stmt, values)

def create_station_update_params(st_dict):
    return (st_dict['bikes'], st_dict['docks'],
            st_dict['total'], st_dict['max_total'],
            st_dict['poll_time'], st_dict['lc'], st_dict['lu'], 
            st_dict['id'])

def update_station(conn, values):
    update_stmt = """UPDATE stations
    SET bikes=?, docks=?, curr_total=?, max_total=?, poll_time=?,
    lc=?, lu=?
    WHERE id=?"""
    cursor = conn.cursor()
    cursor.execute(update_stmt, values)

def select_station(conn, station_id):
    select_stmt = """SELECT name, bikes, docks, curr_total, max_total
    FROM stations WHERE id=?"""
    cursor = conn.cursor()
    cursor.execute(select_stmt, (station_id,))
    db_station = cursor.fetchone()
    return db_station

def insert_count(conn, values):
    insert_stmt = """INSERT INTO counts
    (station_id, bikes, docks, poll_time) VALUES (?, ?, ?, ?)"""
    cursor = conn.cursor()
    cursor.execute(insert_stmt, values)

def select_last_count(conn, station_id):
    select_stmt = """SELECT bikes, docks FROM counts WHERE station_id=?
    ORDER BY poll_time DESC LIMIT 1"""
    cursor = conn.cursor()
    cursor.execute(select_stmt, (station_id,))
    count_row = cursor.fetchone()
    if count_row != None:
        bikes = count_row['bikes']
        docks = count_row['docks']
        return (bikes, docks)
    else:
        return (0, 0)

def create_station_dict(station, timestamp):
    """Extract/transform attributes from original dict loaded from json
    and add the poll_time"""
    st_dict = {}
    st_dict['id'] = station['n']
    st_dict['name'] = station['s']
    st_dict['lc'] = int(station['lc']/1000)
    st_dict['lu'] = int(station['lu']/1000)
    st_dict['bikes'] = int(station['ba'])
    st_dict['docks'] = int(station['da'])
    st_dict['total'] = st_dict['docks'] + st_dict['bikes']
    st_dict['poll_time'] = timestamp
    return st_dict

def create_count_params(st_dict):
    return (st_dict['id'], st_dict['bikes'], st_dict['docks'],
            st_dict['poll_time'])

                                                             
def process_db_station(conn, st_dict):
    """Updates the stations table with the current station while
    making sure the maximum total of docks and bikes is preserved
    and then returning the max total"""
    # save db_station if not previously saved
    db_station = select_station(conn, st_dict['id'])
    if db_station == None:
        st_dict['max_total'] = 0
        value_params = create_station_insert_params(st_dict)
        insert_station(conn, value_params)
        db_station = select_station(conn, st_dict['id'])
    if db_station == None:
        raise AssertionError("db_station is missing")

    # update db_station if its total has increased (to new maximum)
    total = st_dict['total']
    db_total = db_station['max_total']
    max_total = total if total > db_total else db_total
    if db_total != max_total:
        total_diff = max_total - db_total
        print("Max total has changed by %d at %s %s" %
              (total_diff, st_dict['id'], st_dict['name']))
    # update station in the database
    st_dict['max_total'] = max_total
    value_params = create_station_update_params(st_dict)
    update_station(conn, value_params)
    return max_total

    
def process_stations(stations_ary, poll_time):
    # check if on Windows or Linux
    windows_path = [os.sep, 'Users', 'John', 'Documents', 
    'Share_VirtualBox',]
    linux_path = [os.sep, 'media', 'sf_Share_VirtualBox',]

    if platform.system() == 'Linux':
        db_path = linux_path.copy()
    else:
        db_path = windows_path.copy()
    db_path.append('db.sqlite3')
    sqlite_file = os.path.join(*db_path)

    # Connecting to the database file
    conn = sqlite3.connect(sqlite_file)
    conn.row_factory = sqlite3.Row
        
    for station in stations_ary:
        # transform attributes of json station
        st_dict = create_station_dict(station, poll_time)

        # determine any change in counts between last saved count and now
        # for now, this is limited to the total and not bikes/docks
        curr_total = st_dict['total']        
        (db_bikes, db_docks) = select_last_count(conn, st_dict['id'])
        last_total = db_bikes + db_docks
        diff = curr_total - last_total
        
        # save new count if different
        if diff != 0:
            value_params = create_count_params(st_dict)
            insert_count(conn, value_params)
        
        max_total = process_db_station(conn, st_dict)

        # detect non-availability of bikes or docks and save to lists 
        # detect_non_availability(st_dict)
        
        # calculate delta for the total
        delta = curr_total - last_total
        max_diff = max_total - curr_total
        station_id = st_dict['id']
        station_name = st_dict['name']
        if delta != 0:
            print("Change of %d at %s %s" % (diff, station_id, station_name))
            # save to events table
        if st_dict['bikes'] == 0:
            # save to status table
            print("No bikes at %s %s" % (station_id, station_name))
            pass
        if st_dict['docks'] == 0:
            # save to status table
            print("No docks at %s %s" % (station_id, station_name))
            pass
        if max_diff > 0:
            print("%d from max at %s %s" % (max_diff, station_id, station_name))
    conn.commit()
    conn.close()
	
def run():
    station_ary, poll_time = get_stations()
    process_stations(station_ary, poll_time)
    
if __name__ == "__main__":
	run()
    
