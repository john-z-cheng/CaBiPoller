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

def insert_ref_station(conn, st_dict):
    cursor = conn.cursor()
    insert_stmt = """INSERT into ref_stations (id, name, dock_qty, lat, lon, jurisdiction)
                     VALUES (?, ?, ?, ?, ?, ?)"""
    values = (st_dict['id'], st_dict['name'], 0,
              st_dict['lat'], st_dict['lon'], st_dict['jurisdiction'])
    cursor.execute(insert_stmt, values)
    return st_dict['id']
    
def create_station_insert_params(st_dict):
    return (st_dict['id'], st_dict['bikes'], st_dict['docks'], st_dict['inactives'],
			st_dict['poll_time'], st_dict['lu'], st_dict['lc'])

def insert_curr_station(conn, st_dict):
    """Creates the row in the curr_stations table with all columns as
    NULL except for the primary id"""
    
    cursor = conn.cursor()

    # check if ref_station exists and if not, insert an instance with 0 dock_qty
    select_stmt = """SELECT * FROM ref_stations WHERE id=?"""
    cursor.execute(select_stmt, (st_dict['id'],))
    row = cursor.fetchone()
    if row == None:
        # create ref_station
        insert_ref_station(conn, st_dict)
    
    insert_stmt = """INSERT INTO curr_stations (station_id) VALUES (?)"""
    cursor.execute(insert_stmt, (st_dict['id'],))

def create_station_update_params(st_dict):
    return (st_dict['bikes'], st_dict['docks'], st_dict['inactives'],
            st_dict['a_state'], st_dict['d_state'],
            st_dict['poll_time'], st_dict['lc'], st_dict['lu'],
            st_dict['a_start'], st_dict['d_start'],
            st_dict['id'])

def update_curr_station(conn, st_dict):
    values = create_station_update_params(st_dict)
    update_stmt = """UPDATE curr_stations
    SET bikes=?, docks=?, inactives=?, available_state=?, defective_state=?,
	poll_time=?, lu=?, lc=?, available_start=?, defective_start=?
    WHERE station_id=?"""
    cursor = conn.cursor()
    cursor.execute(update_stmt, values)

def select_curr_station(conn, station_id):
    select_stmt = """SELECT * FROM curr_stations WHERE station_id=?"""
    cursor = conn.cursor()
    cursor.execute(select_stmt, (station_id,))
    db_station = cursor.fetchone()
    return db_station

def create_station_dict(station, timestamp):
    """Extract/transform attributes from original dict loaded from json
    and add the poll_time"""
    st_dict = {}
    if 'n' in station: st_dict['id'] = station['n']
    if 's' in station: st_dict['name'] = station['s']
    if 'd' in station: st_dict['jurisdiction'] = station['d'][10:]
    if 'la' in station: st_dict['lat'] = station['la']
    if 'lo' in station: st_dict['lon'] = station['lo']
    if 'lc' in station: st_dict['lc'] = int(station['lc']/1000)
    else: st_dict['lc'] = 0
    if 'lu' in station: st_dict['lu'] = int(station['lu']/1000)
    else: st_dict['lu'] = 0
    if 'ba' in station: st_dict['bikes'] = int(station['ba'])
    if 'da' in station: st_dict['docks'] = int(station['da'])
    st_dict['poll_time'] = timestamp
    return st_dict

def get_dock_qty(conn, station_id):
    select_stmt = """SELECT dock_qty FROM ref_stations WHERE id=?"""
    cursor = conn.cursor()
    cursor.execute(select_stmt, (station_id,))
    row = cursor.fetchone()
    if row != None:
        return row[0]
    else:
        return 0
                                                         
def get_db_station(conn, st_dict):
    """Updates the curr_stations table with the current values while
    making sure the maximum total of docks and bikes is preserved
    and then returning the max total"""
    # save db_station if not previously saved
    db_dict = select_curr_station(conn, st_dict['id'])
    if db_dict == None:
        insert_curr_station(conn, st_dict)
        db_dict = select_curr_station(conn, st_dict['id'])
    if db_dict == None:
        raise AssertionError("db_station is missing")
    db_station = dict()
    for key in db_dict.keys():
        db_station[key] = db_dict[key]
    # get the dock_qty and include in the db_station
    db_station['dock_qty'] = get_dock_qty(conn, st_dict['id'])
    db_station['a_state'] = db_station['available_state']
    db_station['d_state'] = db_station['defective_state']
    return db_station

def create_count_params(state_type, st_dict):
    return (st_dict['id'], state_type,
            st_dict['bikes'], st_dict['docks'], st_dict['inactives'],
            st_dict['poll_time'], st_dict['lu'])

def insert_count_history(conn, state_type, st_dict):
    values = create_count_params(state_type, st_dict)
    insert_stmt = """INSERT INTO count_history
    (station_id, state_type, bikes, docks, inactives, poll_time, lu)
    VALUES (?, ?, ?, ?, ?, ?, ?)"""
    cursor = conn.cursor()
    cursor.execute(insert_stmt, values)

def deduce_current_state(st_dict, db_dict):
    # calculate the new value for inactives for st_dict
    total = st_dict['bikes'] + st_dict['docks']
    st_dict['inactives'] = db_dict['dock_qty'] - total

    # determine the current available_state
    if (st_dict['bikes'] != 0 and st_dict['docks'] != 0):
        st_dict['a_state'] = 'acceptable'
    elif (st_dict['bikes'] == 0):
        st_dict['a_state'] = 'empty'
    elif (st_dict['docks'] == 0):
        st_dict['a_state'] = 'full'
    else:
        # both bikes and docks are 0 which is very unusual
        st_dict['a_state'] = 'unavailable'
    
    # determine the current defective_state
    if st_dict['inactives'] == 0:
        st_dict['d_state'] = 'acceptable'
    elif st_dict['inactives'] > 0:
        st_dict['d_state'] = 'unacceptable'
    else:
        # negative means dock_qty could be wrong in ref_stations
        st_dict['d_state'] = 'unexpected'

def create_state_params(state_type, st_dict, db_dict):
    if state_type == 'available':
        new_state = st_dict['a_state']
        old_state = db_dict['a_state']
    elif state_type == 'defective':
        new_state = st_dict['d_state']
        old_state = db_dict['d_state']
    return (st_dict['id'], st_dict['poll_time'],
            state_type, old_state, new_state)

def insert_state_history(conn, state_type, st_dict, db_dict):
    values = create_state_params(state_type, st_dict, db_dict)
    insert_stmt = """INSERT INTO state_history
    (station_id, change_time, state_type, old_state, new_state)
    VALUES (?, ?, ?, ?, ?)"""
    cursor = conn.cursor()
    cursor.execute(insert_stmt, values)

def update_history(conn, st_dict, db_dict):
    needs_update = False

    # check for change in counts for available bikes or docks
    if ((db_dict['bikes'] != st_dict['bikes']) or
        (db_dict['docks'] != st_dict['docks'])):
        insert_count_history(conn, 'available', st_dict)
        needs_update = True

    # check for change in counts for defective docks
    if (db_dict['inactives'] != st_dict['inactives']):
        insert_count_history(conn, 'defective', st_dict)
        needs_update = True

    # check for missing start timestamp for states
    # which may have happened for a database schema change

    st_dict['a_start'] = db_dict['available_start']
    if ((st_dict['a_start'] == None) or (st_dict['a_start'] == 0)):
        st_dict['a_start'] = st_dict['poll_time']
        needs_update = True
    st_dict['d_start'] = db_dict['defective_start']
    if ((st_dict['d_start'] == None) or (st_dict['d_start'] == 0)):
        st_dict['d_start'] = st_dict['poll_time']
        needs_update = True

    # check for change in available state
    if (st_dict['a_state'] != db_dict['a_state']):
        insert_state_history(conn, 'available', st_dict, db_dict)
        st_dict['a_start'] = st_dict['poll_time']
        needs_update = True
    if (st_dict['d_state'] != db_dict['d_state']):
        insert_state_history(conn, 'defective', st_dict, db_dict)
        st_dict['d_start'] = st_dict['poll_time']
        needs_update = True

    # for any insert to history, update curr_station 
    if needs_update:
        update_curr_station(conn, st_dict)
        return True
    else:
        return False

	
def process_stations(stations_ary, timestamp):
    # check if on Windows or Linux
    windows_path = [os.sep, 'Users', 'John', 'Documents', 'Share_VirtualBox',]
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
        st_dict = create_station_dict(station, timestamp)

        # get the previous state
        db_dict = get_db_station(conn, st_dict)

        # get the new current state 
        deduce_current_state(st_dict, db_dict)

	# detect and save any change in states
        update_history(conn, st_dict, db_dict)		
        
    conn.commit()
    conn.close()

			
def run():
    station_ary, timestamp = get_stations()
    process_stations(station_ary, timestamp)
    
if __name__ == "__main__":
    run()
    
