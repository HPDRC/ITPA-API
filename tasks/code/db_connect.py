import os
#import time
from celery.utils.log import get_task_logger
import datetime

from redisjson import (redis_load, redis_set, ejson_loads, ejson_dumps, redis_set_records, get_polygon_features_from_array)

from utils import (get_date_isoformat, query_sql, exec_sql_commit_values, query_delete_stale,
    get_polygon_from, get_eastern_current_day_only)

global_logger = get_task_logger(__name__)

fl511_database_name = 'fl511.'

fl511_congestions_table_name = fl511_database_name + 'congestions'

sql_insert_congestions = 'INSERT INTO ' + fl511_congestions_table_name + ' (congestion_id, coordinate, location, description, last_updated) '
sql_insert_congestions += 'VALUES(%s, geomFromText(\'POINT(%s %s)\'), %s, %s, %s) '
sql_insert_congestions += 'ON DUPLICATE KEY UPDATE coordinate=GeomFromText(\'POINT(%s %s)\'), location=%s, description=%s, last_updated=%s;'

sql_delete_stale_congestions = 'DELETE FROM ' + fl511_congestions_table_name + ' WHERE last_updated < date_sub(%s, interval 1 second);'

def get_fl511_congestions_from_db():
    sql_str = "SELECT congestion_id,X(coordinate),Y(coordinate), location, description"
    sql_str += " FROM " + fl511_congestions_table_name + ";"
    return query_sql(sql_str)

def get_fl511_congestions_query_result_to_array(records):
    return ([
        {
            'id': r[0],
            'lon': r[1],
            'lat': r[2],
            'location': r[3],
            'description': r[4],
        } for r in records
    ])

def get_fl511_congestions(): return get_fl511_congestions_query_result_to_array(get_fl511_congestions_from_db())

def update_fl511_congestions_from_db(): redis_set_records('fl511_congestions', get_fl511_congestions())

#[id, lon, lat]
def update_fl511_congestions_on_db(current_records):
    if current_records != None:
        now_time = datetime.datetime.now();
        update_records = [[record[0], record[1], record[2], record[3], record[4], now_time, record[1], record[2], record[3], record[4], now_time] for record in current_records]
        exec_sql_commit_values(sql_insert_congestions, update_records)
        exec_sql_commit_values(sql_delete_stale_congestions, [[now_time]])
        update_fl511_congestions_from_db()

fl511_cameras_table_name = fl511_database_name + 'cameras'

sql_insert_cameras = 'INSERT INTO ' + fl511_cameras_table_name + ' (camera_id, coordinate, last_updated) '
sql_insert_cameras += 'VALUES(%s, geomFromText(\'POINT(%s %s)\'), %s) '
sql_insert_cameras += 'ON DUPLICATE KEY UPDATE coordinate=GeomFromText(\'POINT(%s %s)\'), last_updated=%s;'

sql_delete_stale_cameras = 'DELETE FROM ' + fl511_cameras_table_name + ' WHERE last_updated < date_sub(%s, interval 1 second);'

def get_fl511_cameras_from_db():
    sql_str = "SELECT camera_id,X(coordinate),Y(coordinate)"
    sql_str += "FROM " + fl511_cameras_table_name + ";"
    return query_sql(sql_str)

def get_fl511_cameras_query_result_to_array(records):
    return ([
        {
            'id': r[0],
            'lon': r[1],
            'lat': r[2],
            'url': 'https://fl511.com/map/Cctv/' + r[0],
        } for r in records
    ])

def get_fl511_cameras(): return get_fl511_cameras_query_result_to_array(get_fl511_cameras_from_db())

def update_fl511_cameras_from_db(): redis_set_records('fl511_cameras', get_fl511_cameras())

#[id, lon, lat]
def update_fl511_cameras_on_db(current_records):
    if current_records != None:
        now_time = datetime.datetime.now();
        update_records = [[record[0], record[1], record[2], now_time, record[1], record[2], now_time] for record in current_records]
        exec_sql_commit_values(sql_insert_cameras, update_records)
        exec_sql_commit_values(sql_delete_stale_cameras, [[now_time]])
        update_fl511_cameras_from_db()

fl511_message_boards_database_name = 'fl511_message_boards.'

fl511_message_boards_table_name = fl511_message_boards_database_name + 'fl511_message_boards'
fl511_message_board_current_table_name = fl511_message_boards_database_name + 'fl511_message_board_current'
fl511_message_board_archive_table_name = fl511_message_boards_database_name + 'fl511_message_board_archive'

sql_insert_msg_boards = 'INSERT INTO ' + fl511_message_boards_table_name + ' (board_id, coordinate) '
sql_insert_msg_boards += 'VALUES(%s, geomFromText(\'POINT(%s %s)\')) '
sql_insert_msg_boards += 'ON DUPLICATE KEY UPDATE coordinate=GeomFromText(\'POINT(%s %s)\');'

sql_get_msg_board = 'SELECT id, last_message, last_message_on, X(coordinate) as x, Y(coordinate) as y '
sql_get_msg_board += 'FROM ' + fl511_message_boards_table_name + ' WHERE board_id=%s;'

sql_update_msg_boards = 'UPDATE ' + fl511_message_boards_table_name + ' SET '
sql_update_msg_boards += 'location=%s,region=%s,highway=%s,last_message=%s,'
sql_update_msg_boards += 'last_message_on=%s,last_updated=%s WHERE board_id=%s;'

sql_add_to_msg_boards_history = 'INSERT INTO ' + fl511_message_board_archive_table_name + ' (board_id,message,message_on) VALUES(%s,%s,%s);'

sql_insert_msg_board_current = 'INSERT INTO ' + fl511_message_board_current_table_name + ' (id,location,region,highway,'
sql_insert_msg_board_current += 'coordinate,last_message,last_message_on,board_id,last_updated) '
sql_insert_msg_board_current += 'VALUES(%s,%s,%s,%s,GeomFromText(\'POINT(%s %s)\'),%s,%s,%s,'
sql_insert_msg_board_current += '%s) ON DUPLICATE KEY UPDATE '
sql_insert_msg_board_current += 'location=%s,region=%s,highway=%s,coordinate=GeomFromText(\'POINT(%s %s)\'),'
sql_insert_msg_board_current += 'last_message=%s,last_message_on=%s,'
sql_insert_msg_board_current += 'last_updated=%s;'

sql_delete_stale_msg_board_current = 'DELETE FROM ' + fl511_message_board_current_table_name + ' WHERE last_updated < date_sub(%s, interval 1 second);'

def get_fl511_message_select_prefix():
    sql_str = "SELECT id,location,region,highway,"
    sql_str += "last_message,last_message_on,last_updated, board_id,"
    sql_str += "X(coordinate),Y(coordinate) "
    sql_str += "FROM "
    return sql_str

def get_fl511_message_boards_select(): return get_fl511_message_select_prefix() + fl511_message_boards_table_name + ";"
def get_fl511_message_board_current_select(): return get_fl511_message_select_prefix() + fl511_message_board_current_table_name + ";"

def get_current_fl511_message_boards_from_db(): return query_sql(get_fl511_message_boards_select())
def get_current_fl511_messages_from_db(): return query_sql(get_fl511_message_board_current_select())

def get_fl511_query_result_to_array(records):
    return ([
        {
            'id': r[0], 
            'location': r[1],
            'region': r[2],
            'highway' : r[3],
            'message': r[4],
            'message_on': get_date_isoformat(r[5]),
            'last_updated': get_date_isoformat(r[6]),
            'external_id': r[7],
            'lon': r[8],
            'lat': r[9],
        } for r in records
    ])

def get_current_fl511_message_boards(): return get_fl511_query_result_to_array(get_current_fl511_message_boards_from_db())
def get_current_fl511_messages(): return get_fl511_query_result_to_array(get_current_fl511_messages_from_db())

def update_fl511_message_board_from_db():
    redis_set_records('fl511_message_boards_current', get_current_fl511_message_boards())

#[board_id, board_lon, board_lat]
def update_fl511_message_boards_on_db(current_fl511_message_boards):
    if current_fl511_message_boards != None:
        update_records = [[msg[0], msg[1], msg[2], msg[1], msg[2]] for msg in current_fl511_message_boards] 
        exec_sql_commit_values(sql_insert_msg_boards, update_records)
        update_fl511_message_board_from_db()

def update_fl511_messages_from_db():
    redis_set_records('fl511_messages_current', get_current_fl511_messages())

#[board_id, last_message, highway, region, last_message_on, location]
def update_fl511_messages_on_db(current_fl511_messages):
    if current_fl511_messages != None:
        now_time = datetime.datetime.now();
        update_board_records = []
        add_to_msg_history_records = []
        add_to_msg_current_records = []
        for msg in current_fl511_messages:
            try:
                new_message = msg[1]
                if new_message != None and len(new_message) > 0:
                    new_board_id = msg[0]
                    res = query_sql(sql_get_msg_board, [new_board_id])
                    if res != None and len(res) == 1:
                        res = res[0]

                        board_id = res[0]
                        last_message = res[1]
                        last_message_on = res[2]
                        board_lon = res[3]
                        board_lat = res[4]

                        new_highway = msg[2]
                        new_region = msg[3]
                        new_message_on = msg[4]
                        new_location = msg[5]

                        if last_message_on == None or (last_message_on < msg[4] and last_message != msg[1]):
                            update_record = [new_location, new_region, new_highway, new_message, 
                                new_message_on, now_time, new_board_id]
                            update_board_records.append(update_record) 
                                
                            update_record = [board_id, new_message, new_message_on]
                            add_to_msg_history_records.append(update_record) 

                        update_record = [board_id, new_location, new_region, new_highway,
                            board_lon, board_lat, new_message, new_message_on, new_board_id, now_time,
                            new_location, new_region, new_highway, board_lon, board_lat,
                            new_message, new_message_on, now_time]
                        add_to_msg_current_records.append(update_record)

            except mysql.connector.Error as dbError:
                global_logger.error('update_fl511_messages_on_db: ' + str(dbError.msg))
            except Exception as cerror:
                global_logger.error('update_fl511_messages_on_db: ' + str(cerror))

        exec_sql_commit_values(sql_update_msg_boards, update_board_records)
        exec_sql_commit_values(sql_add_to_msg_boards_history, add_to_msg_history_records)
        exec_sql_commit_values(sql_insert_msg_board_current, add_to_msg_current_records)
        exec_sql_commit_values(sql_delete_stale_msg_board_current, [[now_time]])
        update_fl511_messages_from_db()

flhsmv_incidents_database_name = 'flhsmv_incidents.'

flhsmv_incidents_archive_table_name = flhsmv_incidents_database_name + 'flhsmv_incidents_archive'
flhsmv_incidents_current_table_name = flhsmv_incidents_database_name + 'flhsmv_incidents_current'

def get_insert_update_incidents(is_archive):
    table_name = flhsmv_incidents_archive_table_name if is_archive else flhsmv_incidents_current_table_name
    sql_str = "INSERT INTO " + table_name + " ("
    if not is_archive: sql_str += "id,"
    sql_str += "external_id, type, date, coordinate, location, county, remarks, last_updated"
    sql_str += ") VALUES("
    if not is_archive: sql_str += "%s,"
    sql_str += "%s,%s,%s,GeomFromText(\"POINT(%s %s)\"),%s,%s,%s,%s"
    sql_str += ") ON DUPLICATE KEY UPDATE "
    sql_str += "type=%s,date=%s,coordinate=GeomFromText(\"POINT(%s %s)\"),location=%s,county=%s,remarks=%s,last_updated=%s"
    sql_str += ";"
    return sql_str;

sql_insert_update_incidents_archive = get_insert_update_incidents(True)
sql_insert_update_incidents_current = get_insert_update_incidents(False)

sql_delete_incidents_current = 'DELETE FROM ' + flhsmv_incidents_current_table_name + ' WHERE last_updated < date_sub(%s, interval 1 second);'

sql_select_from_incidents_archive = "SELECT id,external_id,type,date,X(coordinate),Y(coordinate),location,county,remarks,last_updated "
sql_select_from_incidents_archive += "FROM " + flhsmv_incidents_archive_table_name + " WHERE last_updated >= date_sub(%s, interval 1 second);"

def get_current_flhsmv_incidents_from_db():
    sql_str = "SELECT id,external_id,type,date,X(coordinate),Y(coordinate),location,county,remarks,last_updated "
    sql_str += "FROM " + flhsmv_incidents_current_table_name + ";"
    return query_sql(sql_str)

def get_flhsmv_query_result_to_array(records):
    return ([
        {
            'id': r[0], 
            'external_id': r[1],
            'type': r[2],
            'date' : get_date_isoformat(r[3]),
            'lon': r[4],
            'lat': r[5],
            'location': r[6],
            'county': r[7],
            'remarks': r[8],
            'last_updated': get_date_isoformat(r[9]),
        } for r in records
    ])

def get_current_flhsmv_incidents(): return get_flhsmv_query_result_to_array(get_current_flhsmv_incidents_from_db())

def update_flhsmv_incidents_from_db(): 
    redis_set_records('flhsmv_incidents_current', get_current_flhsmv_incidents())

#[inc_id, inc_type, inc_datetime, inc_lon, inc_lat, inc_location, inc_county, inc_remarks]
def update_flhsmv_incidents_on_db(current_flhsmv_incidents):
    if current_flhsmv_incidents != None:
        now_time = datetime.datetime.now();
        insert_update_to_archive = []
        for r in current_flhsmv_incidents:
            record = []
            record.extend(r)
            record.append(now_time)
            record.extend(r[1:])
            record.append(now_time)
            insert_update_to_archive.append(record)
        exec_sql_commit_values(sql_insert_update_incidents_archive, insert_update_to_archive)
        archive_records_updated = query_sql(sql_select_from_incidents_archive, [now_time])
        insert_update_to_current = []
        for r in archive_records_updated:
            record = []
            record.extend(r)
            record.extend(r[2:])
            insert_update_to_current.append(record)
        exec_sql_commit_values(sql_insert_update_incidents_current, insert_update_to_current)
        exec_sql_commit_values(sql_delete_incidents_current, [[now_time]])
        update_flhsmv_incidents_from_db()


parking_database_name = 'itpa_parking.'

parking_sites_table_name = parking_database_name + 'parking_sites'
parking_site_types_table_name = parking_database_name + 'parking_site_types'

sql_get_parking_sites = "SELECT ps.id, ps.type_id, ps_type.identifier, ps.identifier,"
sql_get_parking_sites += "asText(ps.polygon),ps.number_of_levels,"
sql_get_parking_sites += "x(ps.centroid),y(ps.centroid), ps.capacity,ps.is_active "
sql_get_parking_sites += "FROM " + parking_sites_table_name + " ps, " + parking_site_types_table_name + " ps_type"

sql_get_valid_parking_sites = sql_get_parking_sites + " WHERE polygon IS NOT NULL and centroid IS NOT NULL and is_active and ps_type.id = ps.type_id ORDER BY ps.id"

sql_get_all_parking_sites = sql_get_parking_sites + " WHERE ps_type.id = ps.type_id ORDER BY ps.id"

def get_valid_parking_sites_from_db(): return query_sql(sql_get_valid_parking_sites)
def get_all_parking_sites_from_db(): return query_sql(sql_get_all_parking_sites)

def get_parking_site_query_result_to_array(records):
    return ([
        { 
            'id': r[0],
            'type_id': r[1],
            'type_name': r[2],
            'identifier': r[3], 
            'polygon': get_polygon_from(r[4]),
            'number_of_levels': r[5],
            'lon': r[6],
            'lat': r[7],
            'centroid': [r[6], r[7]] if r[6] != None and r[7] != None else None,
            'capacity': r[8],
            'is_active' : r[9] == 1
        } for r in records
    ])

def update_parking_sites_from_db():
    redis_set_records('itpa_parking_sites', get_parking_site_query_result_to_array(get_valid_parking_sites_from_db()), get_polygon_features_from_array)
    redis_set_records('itpa_parking_sites_all', get_parking_site_query_result_to_array(get_all_parking_sites_from_db()), get_polygon_features_from_array)

def get_bus_query_result_to_array(records):
    return ([
        {
            'fleet': r[0],
            'id': r[1], 
            'name': r[2],
            'route_id': r[3],
            'direction': r[4],
            'trip_id': r[5],
            'lon': r[6],
            'lat': r[7],
            'coordinate_updated': get_date_isoformat(r[8]),
            'occupancy_percentage' : r[9],
            'speed_mph' : r[10],
            'heading_degree' : r[11],
            'last_updated': get_date_isoformat(r[12]),
        } for r in records
    ])

transit_database_name = 'itpa_transit.'

current_buses_table_name = transit_database_name + 'current_buses'
archive_buses_table_name = transit_database_name + 'archive_buses'

sql_insert_update_current_buses = 'INSERT INTO ' + current_buses_table_name + ' ('
sql_insert_update_current_buses += 'fleet,id,name,route_id,direction,trip_id,coordinate,coordinate_updated,occupancy_percentage,speed_mph,heading_degree,last_updated'
sql_insert_update_current_buses += ') VALUES ('
sql_insert_update_current_buses += '%s,%s,%s,%s,%s,%s,geomFromText("POINT(%s %s)"),%s,%s,%s,%s,%s'
sql_insert_update_current_buses += ') ON DUPLICATE KEY UPDATE '
sql_insert_update_current_buses += 'name=%s,route_id=%s,direction=%s,trip_id=%s,coordinate=GeomFromText("POINT(%s %s)"),coordinate_updated=%s,'
sql_insert_update_current_buses += 'occupancy_percentage=%s,speed_mph=%s,heading_degree=%s,last_updated=%s'
sql_insert_update_current_buses += ';'

sql_insert_archive_buses = 'INSERT INTO ' + archive_buses_table_name + ' ('
sql_insert_archive_buses += 'fleet,id,name,route_id,direction,trip_id,coordinate,coordinate_updated,occupancy_percentage,speed_mph,heading_degree'
sql_insert_archive_buses += ') VALUES ('
sql_insert_archive_buses += '%s,%s,%s,%s,%s,%s,geomFromText("POINT(%s %s)"),%s,%s,%s,%s'
sql_insert_archive_buses += ');'

sql_get_current_buses = "SELECT fleet,id,name,route_id,direction,trip_id,X(coordinate),Y(coordinate),coordinate_updated,occupancy_percentage,speed_mph,heading_degree,last_updated "
sql_get_current_buses += "FROM " + current_buses_table_name
#sql_get_current_buses += " WHERE coordinate_updated > date_sub(current_timestamp(), interval 600 second);";
#sql_get_current_buses += " WHERE last_updated > date_sub(current_timestamp(), interval 600 second);";
sql_get_current_buses += " WHERE last_updated > date_sub(current_timestamp(), interval 3600 second);";

sql_select_stale_current_bus_ids = "SELECT fleet, id FROM " + current_buses_table_name
sql_select_stale_current_bus_ids += " WHERE fleet=%s and last_updated < date_sub(%s, interval 5 second) ORDER BY fleet ASC, id ASC;"

sql_delete_current_bus_by_ids = "DELETE FROM " + current_buses_table_name + " WHERE fleet= %s and id=%s;"

def get_current_buses_from_db(): return query_sql(sql_get_current_buses)

def update_buses_from_db(): 
    redis_set_records('itpa_buses_current', get_bus_query_result_to_array(get_current_buses_from_db()))

#[fleet, bus_id, bus_name, route_id, direction, trip_id, longitude, latitude, date_updated, occupancy_percentage, speed_mph, heading]
def update_buses_on_db(current_buses, archive_buses):
    fleet = None
    now_time = datetime.datetime.now();
    if current_buses != None and len(current_buses) > 0:
        insert_update_to_current = []
        fleet = current_buses[0][0]
        for r in current_buses:
            record = []
            r.append(now_time)
            record.extend(r)
            record.extend(r[2:])
            insert_update_to_current.append(record)
        exec_sql_commit_values(sql_insert_update_current_buses, insert_update_to_current)
    if archive_buses != None and len(archive_buses) > 0:
        if fleet == None: fleet = archive_buses[0][0]
        exec_sql_commit_values(sql_insert_archive_buses, archive_buses)
    if fleet != None:
        query_delete_stale(sql_select_stale_current_bus_ids, [fleet, now_time], sql_delete_current_bus_by_ids)
        """
        fleeds_and_ids_to_del = query_sql(sql_select_stale_current_bus_ids, [fleet, now_time])
        if fleeds_and_ids_to_del != None and len(fleeds_and_ids_to_del) > 0:
            exec_sql_commit_values(sql_delete_current_bus_by_ids, fleeds_and_ids_to_del)
        """

bus_stops_table_name = transit_database_name + 'bus_stops'

sql_get_bus_stops = "SELECT fleet, id, `code`, `name`, `desc`, X(coordinate), Y(coordinate), last_updated"
sql_get_bus_stops += " FROM " + bus_stops_table_name
sql_get_bus_stops += " ORDER BY fleet ASC, id ASC;"

sql_insert_update_bus_stops = 'INSERT INTO ' + bus_stops_table_name + ' ('
sql_insert_update_bus_stops += 'fleet,id,`code`,`name`,`desc`,coordinate,last_updated'
sql_insert_update_bus_stops += ') VALUES ('
sql_insert_update_bus_stops += '%s,%s,%s,%s,%s,geomFromText("POINT(%s %s)"),%s'
sql_insert_update_bus_stops += ') ON DUPLICATE KEY UPDATE '
sql_insert_update_bus_stops += '`code`=%s,`name`=%s,`desc`=%s,coordinate=GeomFromText("POINT(%s %s)"),last_updated=%s'
sql_insert_update_bus_stops += ';'

sql_select_stale_bus_stop_ids = "SELECT fleet, id FROM " + bus_stops_table_name
sql_select_stale_bus_stop_ids += " WHERE fleet=%s and last_updated < date_sub(%s, interval 5 second) ORDER BY fleet ASC, id ASC;"

sql_delete_bus_stops_by_ids = "DELETE FROM " + bus_stops_table_name + " WHERE fleet= %s and id=%s;"

def get_bus_stop_query_result_to_array(records):
    return ([
        {
            'fleet': r[0],
            'id': r[1], 
            'code': r[2],
            'name': r[3],
            'desc': r[4],
            'lon': r[5],
            'lat': r[6],
            'last_updated': get_date_isoformat(r[7]),
        } for r in records
    ])

def get_bus_stops_from_db(): return query_sql(sql_get_bus_stops)

def update_itpa_bus_stops_from_db():
    redis_set_records('itpa_bus_stops', get_bus_stop_query_result_to_array(get_bus_stops_from_db()))

#fleet, stop_id, code, name, desc, lon, lat
def update_itpa_bus_stops_on_db(bus_stops_records):
    if bus_stops_records != None and len(bus_stops_records) > 0:
        fleet = bus_stops_records[0][0]
        now_time = datetime.datetime.now();
        insert_update_records = []
        for r in bus_stops_records:
            record = []
            r.append(now_time)
            record.extend(r)
            record.extend(r[2:])
            insert_update_records.append(record)
        exec_sql_commit_values(sql_insert_update_bus_stops, insert_update_records)
        query_delete_stale(sql_select_stale_bus_stop_ids, [fleet, now_time], sql_delete_bus_stops_by_ids)

bus_routes_table_name = transit_database_name + 'bus_routes'

sql_get_bus_routes = "SELECT fleet, id, `name`, `color`, compressed_multi_linestring, ndirections, direction_names, direction_shapes, compressed_stop_ids, last_updated"
sql_get_bus_routes += " FROM " + bus_routes_table_name
sql_get_bus_routes += " ORDER BY fleet ASC, id ASC;"

sql_insert_update_bus_routes = 'INSERT INTO ' + bus_routes_table_name + ' ('
sql_insert_update_bus_routes += 'fleet,id,`name`,`color`,compressed_multi_linestring, ndirections, direction_names, direction_shapes, compressed_stop_ids, last_updated'
sql_insert_update_bus_routes += ') VALUES ('
sql_insert_update_bus_routes += '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s'
sql_insert_update_bus_routes += ') ON DUPLICATE KEY UPDATE '
sql_insert_update_bus_routes += '`name`=%s,`color`=%s,compressed_multi_linestring=%s,ndirections=%s,direction_names=%s,direction_shapes=%s,compressed_stop_ids=%s,last_updated=%s'
sql_insert_update_bus_routes += ';'

sql_select_stale_bus_route_ids = "SELECT fleet, id FROM " + bus_routes_table_name
sql_select_stale_bus_route_ids += " WHERE fleet=%s and last_updated < date_sub(%s, interval 5 second) ORDER BY fleet ASC, id ASC;"

sql_delete_bus_routes_by_ids = "DELETE FROM " + bus_routes_table_name + " WHERE fleet= %s and id=%s;"

def get_bus_route_query_result_to_array(records):
    return ([
        {
            'fleet': r[0],
            'id': r[1], 
            'name': r[2],
            'color': '#' + r[3],
            'compressed_multi_linestring': ejson_loads(r[4]),
            'ndirections': r[5],
            'direction_names': ejson_loads(r[6]),
            'direction_shapes': ejson_loads(r[7]),
            'compressed_stop_ids': r[8],
            'last_updated': get_date_isoformat(r[9]),
        } for r in records
    ])

def get_bus_routes_from_db(): return query_sql(sql_get_bus_routes)

def update_itpa_bus_routes_from_db():
    redis_set_records('itpa_bus_routes', get_bus_route_query_result_to_array(get_bus_routes_from_db()), None)

#fleet, route_id, route_name, color, compressed_multi_linestring, ndirections, direction_names, direction_shapes, compressed_stop_ids
def update_itpa_bus_routes_on_db(records):
    if records != None and len(records) > 0:
        fleet = records[0][0]
        now_time = datetime.datetime.now();
        insert_update_records = []
        for r in records:
            record = []
            r[4] = ejson_dumps(r[4])
            r[6] = ejson_dumps(r[6])
            r[7] = ejson_dumps(r[7])
            r.append(now_time)
            record.extend(r)
            record.extend(r[2:])
            insert_update_records.append(record)
        exec_sql_commit_values(sql_insert_update_bus_routes, insert_update_records)
        query_delete_stale(sql_select_stale_bus_route_ids, [fleet, now_time], sql_delete_bus_routes_by_ids)

#BUS ETAS

bus_etas_table_name = transit_database_name + 'bus_etas'

sql_get_bus_etas = "SELECT fleet, bus_id, stop_id, route_id, eta, last_updated"
sql_get_bus_etas += " FROM " + bus_etas_table_name
sql_get_bus_etas += " ORDER BY fleet ASC, eta ASC;"

sql_insert_update_bus_etas = 'INSERT INTO ' + bus_etas_table_name + ' ('
sql_insert_update_bus_etas += 'fleet,bus_id,stop_id,route_id,eta,last_updated'
sql_insert_update_bus_etas += ') VALUES ('
sql_insert_update_bus_etas += '%s,%s,%s,%s,%s,%s'
sql_insert_update_bus_etas += ') ON DUPLICATE KEY UPDATE '
sql_insert_update_bus_etas += 'route_id=%s,eta=%s,last_updated=%s'
sql_insert_update_bus_etas += ';'

sql_select_stale_bus_etas_ids = "SELECT fleet, bus_id, stop_id FROM " + bus_etas_table_name
sql_select_stale_bus_etas_ids += " WHERE fleet=%s and last_updated < date_sub(%s, interval 5 second);"

sql_delete_bus_etas_by_ids = "DELETE FROM " + bus_etas_table_name + " WHERE fleet= %s and bus_id=%s and stop_id=%s;"

def get_bus_eta_query_result_to_array(records):
    return ([
        {
            'fleet': r[0],
            'bus_id': r[1],
            'stop_id': r[2],
            'route_id': r[3],
            'eta': get_date_isoformat(r[4]),
            #'last_updated': get_date_isoformat(r[5]),
        } for r in records
    ])

def get_bus_etas_from_db(): return query_sql(sql_get_bus_etas)

def update_itpa_bus_etas_from_db():
    redis_set_records('itpa_bus_etas', get_bus_eta_query_result_to_array(get_bus_etas_from_db()), None)

#fleet, bus_id, stop_id, route_id, est_stop_eta
def update_itpa_bus_etas_on_db(records):
    if records != None and len(records) > 0:
        fleet = records[0][0]
        now_time = datetime.datetime.now();
        insert_update_records = []
        for r in records:
            record = []
            r.append(now_time)
            record.extend(r)
            record.extend(r[3:])
            insert_update_records.append(record)
        exec_sql_commit_values(sql_insert_update_bus_etas, insert_update_records)
        query_delete_stale(sql_select_stale_bus_etas_ids, [fleet, now_time], sql_delete_bus_etas_by_ids)

#PARKING SERVER

def update_parking_decals_on_db(records):
    redis_set_records('itpa_parking_decals', records, None)

def update_parking_recommendations_on_db(records):
    redis_set_records('itpa_parking_recommendations', records, None)

def update_parking_last_events_on_db(records):
    redis_set_records('itpa_parking_last_events', records, None)

redis_key_itpa_parking_availability_from_parking_server = 'itpa_parking_availability_from_parking_server'

def update_parking_availability_on_db(records):
    parking_server_records = redis_load(redis_key_itpa_parking_availability_from_parking_server)
    if parking_server_records != None:
        id_map = {}
        for rec in records:
            site_id = rec.get('site_id')
            if site_id != None:
                id_map[site_id] = True
        for rec in parking_server_records:
            site_id = rec.get('site_id')
            if site_id != None and id_map.get(site_id) == None:
                records.append(rec)
    redis_set_records('itpa_parking_availability', records, None)

def update_parking_server_availabilities_on_db(records):
    redis_set(redis_key_itpa_parking_availability_from_parking_server, records)

#MVIDEO SERVER

def update_bus_feeds_on_db(records):
    redis_set_records('itpa_bus_feeds', records, None)

#ITPA NOTIFICATIONS

messaging_database_name = 'itpa_messaging.'

notifications_table_name = messaging_database_name + 'itpa_notifications'

sql_get_notifications = "SELECT id,title,summary,icon,url,start_on,expire_on,is_active"
sql_get_notifications += " FROM " + notifications_table_name

sql_get_notifications_active_where = \
    " WHERE is_active and (start_on IS NULL or start_on <= %s) and (expire_on IS NULL or expire_on > %s) "

sql_get_notifications_order = " ORDER BY id ASC;"

sql_get_notifications_active = sql_get_notifications + sql_get_notifications_active_where + sql_get_notifications_order;
sql_get_notifications_all = sql_get_notifications + sql_get_notifications_order;

def get_itpa_notifications_active_from_db(): 
    est_datetime_now = get_eastern_current_day_only()
    return query_sql(sql_get_notifications_active, [est_datetime_now, est_datetime_now])

def get_itpa_notifications_all_from_db(): return query_sql(sql_get_notifications_all)

def get_itpa_notification_query_result_to_array(records):
    return ([
        {
            'id': r[0],
            'title': r[1],
            'summary': r[2],
            'icon': r[3],
            'url': r[4],
            'start_on': get_date_isoformat(r[5]),
            'expire_on': get_date_isoformat(r[6]),
            'is_active': r[7] == 1,
        } for r in records
    ])

def update_itpa_notifications_from_db():
    redis_set_records('itpa_notifications_active', get_itpa_notification_query_result_to_array(get_itpa_notifications_active_from_db()), None)
    redis_set_records('itpa_notifications_all', get_itpa_notification_query_result_to_array(get_itpa_notifications_all_from_db()), None)

#STREETSMART

def update_streetsmart_road_graph_on_db(records):
    redis_set_records('streetsmart_road_graph', records, None)

#DEVICE TRACKING

itpa_app_database_name = 'itpa_app.'

archive_device_tracking_table_name = itpa_app_database_name + 'archive_device_tracking'
current_device_tracking_table_name = itpa_app_database_name + 'current_device_tracking'

max_current_device_tracking_records = 1000

sql_current_device_tracking = 'SELECT uuid, X(coordinate), Y(coordinate), coordinate_on, is_stationary, altitude, speed_mph, heading_degree'
sql_current_device_tracking += ' FROM ' + current_device_tracking_table_name
sql_current_device_tracking += ' ORDER BY coordinate_on DESC LIMIT ' + str(max_current_device_tracking_records) + ';'

def get_current_device_tracking_query_result_to_array(records):
    return ([
        {
            'uuid': r[0],
            'lon': r[1],
            'lat': r[2],
            'coordinate_on': get_date_isoformat(r[3]),
            'is_stationary': r[4] == 1,
            'altitude': r[5],
            'speed_mph': r[6],
            'heading_degree': r[7],
        } for r in records
    ])

def get_current_device_tracking_from_db(): return query_sql(sql_current_device_tracking)

def update_current_device_tracking_from_db(): 
    redis_set_records('itpa_current_device_tracking', get_current_device_tracking_query_result_to_array(get_current_device_tracking_from_db()))

