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
    return (st_dict['id'], st_dict['bikes'], st_dict['docks'], st_dict['inactives'],
			st_dict['poll_time'], st_dict['lu'], st_dict['lc'])

def insert_curr_station(conn, station_id):
    """Creates the row in the curr_stations table with all columns as
    NULL except for the primary id"""
    insert_stmt = """INSERT INTO curr_stations (station_id) VALUES (?)"""
    cursor = conn.cursor()
    cursor.execute(insert_stmt, (station_id,))

def create_station_update_params(st_dict):
    return (st_dict['bikes'], st_dict['docks'], st_dict['inactives'],
            st_dict['a_state'], st_dict['d_state'],
            st_dict['poll_time'], st_dict['lc'], st_dict['lu'], 
            st_dict['id'])

def update_curr_station(conn, st_dict):
    values = create_station_update_params(st_dict)
    update_stmt = """UPDATE curr_stations
    SET bikes=?, docks=?, inactives=?, available_state=?, defective_state=?,
	poll_time=?, lu=?, lc=?
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
    st_dict['id'] = station['n']
    st_dict['name'] = station['s']
    st_dict['lc'] = int(station['lc']/1000)
    st_dict['lu'] = int(station['lu']/1000)
    st_dict['bikes'] = int(station['ba'])
    st_dict['docks'] = int(station['da'])
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
        insert_curr_station(conn, st_dict['id'])
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
    
def update_count_history(conn, st_dict, db_dict):
    # calculate the new value for inactives for st_dict
    total = st_dict['bikes'] + st_dict['docks']
    st_dict['inactives'] = db_dict['dock_qty'] - total

    was_inserted = False
    # insert into count_history if any change
    if ((db_dict['bikes'] != st_dict['bikes']) or
        (db_dict['docks'] != st_dict['docks'])):
        insert_count_history(conn, 'available', st_dict)
        was_inserted = True

    if (db_dict['inactives'] != st_dict['inactives']):
        insert_count_history(conn, 'defective', st_dict)
        was_inserted = True

    return was_inserted

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
    

def update_state_history(conn, st_dict, db_dict):
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

    needs_update = False
    if (st_dict['a_state'] != db_dict['a_state']):
        insert_state_history(conn, 'available', st_dict, db_dict)
        needs_update = True
    if (st_dict['d_state'] != db_dict['d_state']):
        insert_state_history(conn, 'defective', st_dict, db_dict)
        
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

        # detect and save any change in counts 
        update_count_history(conn, st_dict, db_dict)

	# detect and save any change in states
        update_state_history(conn, st_dict, db_dict)		
        
    conn.commit()
    conn.close()
	
def old_code():
        (db_bikes, db_docks) = select_last_count(conn, st_dict['id'])
        last_total = db_bikes + db_docks
        diff = curr_total - last_total
        
        # save new count if different
        if diff != 0:
            value_params = create_count_params(st_dict)
            insert_count(conn, value_params)
        
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
			
def run():
    station_ary, timestamp = get_stations()
    process_stations(station_ary, timestamp)
    
if __name__ == "__main__":
    run()
    
