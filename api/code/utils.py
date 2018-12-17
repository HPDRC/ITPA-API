import app
import requests
from requests.auth import HTTPBasicAuth
import os
import json
import datetime
import pytz

from bs4 import BeautifulSoup

import mysql.connector
from mysql.connector import ClientFlag

from redisjson import redis_load, redis_set, redis_expire

FLOWER_SERVER = os.environ.get('FLOWER_SERVER', "flower")
FLOWER_PORT = os.environ.get('FLOWER_PORT', "5555")
FLOWER_USER = os.environ.get('CELERY_USER', "itpa")
FLOWER_PASSWORD = os.environ.get('CELERY_PASSWORD', "itpa")
flower_api_server = FLOWER_SERVER + ':' + FLOWER_PORT + '/api/'
flower_api_url = 'http://' + flower_api_server
flower_start_task_async_url = flower_api_url + 'task/send-task/'

def start_task_async(task_name):
    result = False
    if task_name != None:
        try:
            all_url = flower_start_task_async_url + 'tasks.' + task_name
            r = requests.post(all_url, timeout=10, auth=HTTPBasicAuth(FLOWER_USER, FLOWER_PASSWORD))
            if r.status_code == 200: result = True
            else: app.application.logger.error('start_task_async status: ' + str(r.status_code));
        except Exception as e:
            app.application.logger.error('start_task_async exception: ' + str(e));
            result = False
    return result

def get_eastern_naive_from(a_date):
    utc_date = pytz.utc.localize(a_date);
    eastern_tz = pytz.timezone('US/Eastern')
    est_date = utc_date.astimezone(eastern_tz)
    est_date = datetime.datetime(est_date.year, est_date.month, est_date.day, est_date.hour, est_date.minute, est_date.second, est_date.microsecond)
    return est_date

def get_eastern_current_time_naive():
    try:
        eastern_tz = pytz.timezone('US/Eastern')
        uct_now = datetime.datetime.utcnow()
        uct_now_uct = uct_now.replace(tzinfo=pytz.utc)
        est_now_est = uct_now_uct.astimezone(eastern_tz)
        est_now = datetime.datetime(est_now_est.year, est_now_est.month, est_now_est.day, est_now_est.hour, est_now_est.minute, est_now_est.second, est_now_est.microsecond)
        return est_now
    except Exception as e:
        app.application.logger.error('get_eastern_current_time_naive exception:' + str(e))
    return None

MYSQL_HOST = os.environ.get('MYSQL_HOST', 'db')
MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_ROOT_PASSWORD = os.environ.get('MYSQL_ROOT_PASSWORD', '')

db_connect = {
    "pool_name": "api_pool",
    "pool_size": 5,
    "host": MYSQL_HOST,
    "port": int(MYSQL_PORT),
    "user": MYSQL_USER,
    "password": MYSQL_ROOT_PASSWORD,
    "client_flags": [ClientFlag.FOUND_ROWS],
}

def query_sql(sql_str, value = None):
    global db_connect
    cursor = conn = None
    records = []
    try:
        conn = mysql.connector.connect(**db_connect)
        cursor = conn.cursor()
        cursor.execute(sql_str, value)
        records = cursor.fetchall();
    except Exception as e:
        records = []
        app.application.logger.error('query_sql exception: ' + str(e));
    finally:
        if cursor != None: cursor.close()
        if conn != None: conn.close()
    return records

def exec_sql_commit_values(sql_str, values):
    conn = cursor = None
    ids = []
    try:
        if values != None and len(values) > 0:
            conn = mysql.connector.connect(**db_connect)
            cursor = conn.cursor()
            for value in values:
                cursor.execute(sql_str, value)
                ids.append(cursor.lastrowid)
            conn.commit()
    except mysql.connector.Error as dbError:
        try: conn.rollback()
        except: pass
        app.application.logger.error('exec_sql_commit_values: ' + str(dbError))
    except Exception as cerror:
        try: conn.rollback()
        except: pass
        app.application.logger.error('exec_sql_commit_values: ' + str(cerror))
    finally:
        if cursor != None: cursor.close()
        if conn != None: conn.close()
    return ids

def get_date_isoformat(the_date): return the_date.isoformat() if the_date != None else None

class CompressCodec(object):

    def _py2_round(self, x):
        # The polyline algorithm uses Python 2's way of rounding
        return int(math.copysign(math.floor(math.fabs(x) + 0.5), x))

    def _write(self, curr_value, prev_value, factor):
        output = ''
        curr_value = self._py2_round(curr_value * factor)
        prev_value = self._py2_round(prev_value * factor)
        coord = curr_value - prev_value
        coord <<= 1
        coord = coord if coord >= 0 else ~coord

        while coord >= 0x20:
            output += chr((0x20 | (coord & 0x1f)) + 63)
            coord >>= 5

        output += chr(coord + 63)
        return output

    def _trans(self, value, index):
        byte, result, shift = None, 0, 0

        while byte is None or byte >= 0x20:
            byte = ord(value[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            comp = result & 1

        return ~(result >> 1) if comp else (result >> 1), index

    def encode_values(self, values, precision=5):
        encoded_values_str, factor, ncoords  = '', int(10 ** precision), len(values)
        prev_value = 0
        for i in range(0, ncoords):
            this_value = values[i]
            encoded_values_str += self._write(this_value, prev_value, factor)
            prev_value = this_value
        return encoded_values_str

    def decode_values(self, encoded_values_str, precision=5):
        values, index, value, length, factor = [], 0, 0, len(encoded_values_str), float(10 ** precision)
        while index < length:
            value_change, index = self._trans(encoded_values_str, index)
            value += value_change
            values.append(value / factor)
        return values

    def encodeLS(self, coordinates, precision=5):
        encoded_ls_str, factor, ncoords  = '', int(10 ** precision), len(coordinates)
        prevX = prevY = 0
        for i in range(0, ncoords):
            thisX = coordinates[i][0]
            thisY = coordinates[i][1]
            encoded_ls_str += self._write(thisX, prevX, factor)
            encoded_ls_str += self._write(thisY, prevY, factor)
            prevX = thisX
            prevY = thisY
        return encoded_ls_str

    def decodeLS(self, encoded_ls_str, precision=5):
        coordinates, index, lat, lng, length, factor = [], 0, 0, 0, len(encoded_ls_str), float(10 ** precision)
        while index < length:
            lat_change, index = self._trans(encoded_ls_str, index)
            lng_change, index = self._trans(encoded_ls_str, index)
            lat += lat_change
            lng += lng_change
            coordinates.append((lat / factor, lng / factor))
        return coordinates

user_rights_url = os.environ.get('USER_RIGHTS_URL', 'http://itpa:8060/user_rights')

def get_user_rights(token):
    user_rights = None
    try:
        if token != None:
            all_url = user_rights_url + '?token=' + str(token)
            r = requests.get(all_url, timeout=10)
            user_rights = r.json()
    except Exception as e:
        app.application.logger.error('get_user_rights exception: ' + str(e));
        user_rights = None
    return user_rights

def can_admin_itpa(user_rights): return user_rights != None and user_rights.get('can_admin_itpa') == True

def is_itpa_user(user_rights): return user_rights != None and user_rights.get('is_user') == True

parking_database_name = 'itpa_parking.'

parking_sites_table_name = parking_database_name + 'parking_sites'

def do_add_change_parking_site(form):
    result = False
    added_id = None
    try:
        if form != None:
            identifier = form.get('identifier', None)
            if (identifier != None and len(identifier) > 0):
                id = form.get('id', 0)
                type_id = form.get('type_id', 4)
                type_id = 1 if type_id < 1 else 4 if type_id > 4 else type_id
                centroid = form.get('centroid', {})
                lon = centroid.get('lng')
                lat = centroid.get('lat')
                number_of_levels = form.get('number_of_levels', 1)
                number_of_levels = 1 if number_of_levels < 1 else number_of_levels
                capacity = form.get('capacity', 0)
                encoded_polyline = form.get('encoded_polyline', None)
                is_active = 1 if form.get('is_active', False) else 0
                centroid = 'POINT(' + str(lon) + ' ' + str(lat) + ')' if lon != None and lat != None else None
                polyline = None
                if encoded_polyline != None:
                    cc = CompressCodec()
                    polyline = cc.decodeLS(encoded_polyline, 5)
                    polyline = 'POLYGON((' + ','.join(str(coord[0]) + ' ' + str(coord[1]) for coord in polyline) + '))'
                record = [type_id, identifier, polyline, number_of_levels, centroid, capacity, is_active]
                ids = None
                sql_str = None
                #app.application.logger.error('do_add_change_parking_site: centroid ' + str(centroid));
                if id == 0:
                    sql_str = "INSERT INTO " + parking_sites_table_name + " (type_id,identifier,polygon,number_of_levels,centroid,capacity,is_active) "
                    sql_str += "VALUES(%s,%s,geomfromtext(%s),%s,geomfromtext(%s),%s,%s);";
                elif id > 0:
                    sql_str = "UPDATE " + parking_sites_table_name + " SET "
                    sql_str += "type_id=%s,identifier=%s,polygon=geomfromtext(%s),number_of_levels=%s,centroid=geomfromtext(%s),capacity=%s,is_active=%s"
                    sql_str += " WHERE id=%s;";
                    record.append(id)
                if sql_str != None:
                    ids = exec_sql_commit_values(sql_str, [record])
                    added_id = ids[0] if ids != None and len(ids) > 0 else None
                    result = added_id != None
                    task_result = start_task_async('update_itpa_parking_sites')
            else:
                app.application.logger.error('do_add_change_parking_site: invalid content');
        else:
            app.application.logger.error('do_add_change_parking_site: content missing');
    except Exception as e:
        app.application.logger.error('do_add_change_parking_site: EXCEPTION: ' + str(e));
        result = False
        added_id = None
    return result, added_id

messaging_database_name = 'itpa_messaging.'

itpa_notifications_table_name = messaging_database_name + 'itpa_notifications'

def do_add_change_notification(form):
    result = False
    added_id = None
    try:
        if form != None:
            id = form.get('id', 0)
            title = form.get('title', None)
            summary = form.get('summary', None)
            icon = form.get('icon', None)
            url = form.get('url', None)
            start_on = form.get('start_on', None)
            expire_on = form.get('expire_on', None)
            is_active = 1 if form.get('is_active', False) else 0

            if (title != None and summary != None):
                record = [title, summary, icon, url, start_on, expire_on, is_active]
                ids = None
                sql_str = None
                if id == 0:
                    sql_str = "INSERT INTO " + itpa_notifications_table_name + " (title, summary, icon, url, start_on, expire_on, is_active) "
                    sql_str += "VALUES(%s,%s,%s,%s,%s,%s, %s);";
                elif id > 0:
                    sql_str = "UPDATE " + itpa_notifications_table_name + " SET "
                    sql_str += "title=%s,summary=%s,icon=%s,url=%s,start_on=%s,expire_on=%s,is_active=%s"
                    sql_str += " WHERE id=%s;";
                    record.append(id)
                if sql_str != None:
                    ids = exec_sql_commit_values(sql_str, [record])
                    added_id = ids[0] if ids != None and len(ids) > 0 else None
                    result = added_id != None
                    task_result = start_task_async('update_itpa_notifications')
            else:
                app.application.logger.error('do_add_change_notification: invalid content');
        else:
            app.application.logger.error('do_add_change_notification: content missing');
    except Exception as e:
        app.application.logger.error('do_add_change_notification: EXCEPTION: ' + str(e));
        result = False
        added_id = None
    return result, added_id

transit_table_name = 'itpa_transit.'

archive_buses_table_name = transit_table_name + 'archive_buses'

def get_bus_archive_query_result_to_array(records):
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
            'heading_degree' : r[11]
        } for r in records
    ])

def do_get_buses_history(form):
    result = None
    try:
        if form != None:
            bus_id = form.get('busId', None)
            bus_fleet = form.get('busFleet', None)
            base_date = form.get('baseDate', None)
            time_multiplier = form.get('timeMultiplier', None)
            time_unit = form.get('timeUnit', None)

            if bus_fleet == None: bus_fleet = 'mdt'

            time_multiplier = '1' if time_multiplier == None else str(time_multiplier)
            time_unit = 'hour' if time_unit == None else str(time_unit)

            if base_date != None: base_date = datetime.datetime.strptime(base_date, '%Y-%m-%d %H:%M:%S.%f')
            else: base_date = get_eastern_current_time_naive() - datetime.timedelta(hours=1)

            query_params = [base_date, base_date]

            where_sql = "WHERE (coordinate_updated between %s and date_add(%s, interval " + time_multiplier + " " + time_unit + "))";
            if bus_id != None: 
                bus_id = str(bus_id)
                where_sql += " and id=%s and fleet=%s"
                query_params.extend([bus_id, bus_fleet])

            sql_str = "SELECT fleet,id,name,route_id,direction,trip_id,X(coordinate),Y(coordinate),coordinate_updated,occupancy_percentage,speed_mph,heading_degree"
            sql_str += " FROM " + archive_buses_table_name + " " + where_sql + " order by coordinate_updated ASC;"

            #app.application.logger.error('busId: ' + str(bus_id) + ' time_unit: ' + time_unit);
            #app.application.logger.error('Date: ' + str(base_date) + ' SQL_STR: ' + sql_str);

            result = get_bus_archive_query_result_to_array(query_sql(sql_str, query_params))
        else:
            app.application.logger.error('do_get_buses_history: content missing');
    except Exception as e:
        app.application.logger.error('do_get_buses_history: EXCEPTION: ' + str(e));
        result = None
    return result

itpa_app_database_name = 'itpa_app.'

archive_device_tracking_table_name = itpa_app_database_name + 'archive_device_tracking'
current_device_tracking_table_name = itpa_app_database_name + 'current_device_tracking'

sql_insert_update_current_device_tracking = 'INSERT INTO ' + current_device_tracking_table_name + ' ('
sql_insert_update_current_device_tracking += 'uuid, coordinate, coordinate_on, is_stationary, altitude, speed_mph, heading_degree'
sql_insert_update_current_device_tracking += ') VALUES ('
sql_insert_update_current_device_tracking += '%s,geomFromText(\'POINT(%s %s)\'),%s,%s,%s,%s,%s'
sql_insert_update_current_device_tracking += ') ON DUPLICATE KEY UPDATE '
sql_insert_update_current_device_tracking += 'coordinate=geomFromText(\'POINT(%s %s)\'),coordinate_on=%s,is_stationary=%s,altitude=%s,speed_mph=%s,heading_degree=%s;'

sql_insert_archive_device_tracking = 'INSERT INTO ' + archive_device_tracking_table_name + ' ('
sql_insert_archive_device_tracking += 'uuid, coordinate, coordinate_on, is_stationary, altitude, speed_mph, heading_degree'
sql_insert_archive_device_tracking += ') VALUES ('
sql_insert_archive_device_tracking += '%s,geomFromText(\'POINT(%s %s)\'),%s,%s,%s,%s,%s'
sql_insert_archive_device_tracking += ');'

seconds_expire_app_device_tracking = 60 * 5

def do_track_device(form):
    result = { 'status': False }
    try:
        if form != None:
            uuid = form.get('uuid', None)
            lon = form.get('lon', None)
            lat = form.get('lat', None)
            coordinate_on = form.get('coordinate_on', None)
            altitude = form.get('altitude', None)
            heading_degree = form.get('heading_degree', None)
            speed_mph = form.get('speed_mph', None)
            if (uuid != None and lon != None and lat != None and coordinate_on != None):
                coordinate_on = datetime.datetime.strptime(coordinate_on, '%Y-%m-%d %H:%M:%S.%f')

                uuid = str(uuid)

                lon = float(lon)
                lat = float(lat)

                is_stationary = False
                add_to_archive = True
                skip_out_of_order = False

                if altitude != None: altitude = float(altitude)
                if speed_mph != None: speed_mph = float(speed_mph)
                if heading_degree != None: heading_degree = int(heading_degree)

                redis_key = 'itpa_app_device_track_' + uuid

                last_track = redis_load(redis_key)
                if last_track != None:
                    #app.application.logger.error('FOUND LAST TRACK');
                    last_lon, last_lat, last_coordinate_on = last_track
                    skip_out_of_order = coordinate_on < last_coordinate_on
                    add_to_archive = (last_lon != lon or last_lat != lat) and coordinate_on > last_coordinate_on
                    is_stationary = not add_to_archive

                if not skip_out_of_order:
                    insert_update_current_device_record = [
                        uuid, lon, lat, coordinate_on, is_stationary, altitude, speed_mph, heading_degree,
                        lon, lat, coordinate_on, is_stationary, altitude, speed_mph, heading_degree,
                    ]

                    status = exec_sql_commit_values(sql_insert_update_current_device_tracking, [insert_update_current_device_record])

                    if status != None:
                        #app.application.logger.error('INSERTED/UPDATED CURRENT');
                        if add_to_archive:
                            #app.application.logger.error('ADDING TO ARCHIVE');
                            insert_archive_device_record = [uuid, lon, lat, coordinate_on, is_stationary, altitude, speed_mph, heading_degree,]
                            status = exec_sql_commit_values(sql_insert_archive_device_tracking, [insert_archive_device_record])
                    #else: app.application.logger.error('do_track_device status: ' + str(status));

                    if status != None:
                        #app.application.logger.error('SAVING TO REDIS AND EXPIRE');
                        redis_set(redis_key, (lon, lat, coordinate_on))
                        redis_expire(redis_key, seconds_expire_app_device_tracking)
                        #app.application.logger.error('SAVED TO REDIS AND EXPIRE');

                else:
                    #app.application.logger.error('SKIP OUT OF ORDER');
                    status = True

                result = { 'status': status != None }
            else:
                app.application.logger.error('do_track_device: fields missing');
        else:
            app.application.logger.error('do_track_device: content missing');
    except Exception as e:
        app.application.logger.error('do_track_device: EXCEPTION: ' + str(e));
        result = { 'status': False }
    return result

def get_device_tracking_archive_query_result_to_array(records):
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

def do_get_device_tracking_history(form):
    result = None
    try:
        if form != None:
            uuid = form.get('uuid', None)
            base_date = form.get('baseDate', None)
            time_multiplier = form.get('timeMultiplier', None)
            time_unit = form.get('timeUnit', None)

            time_multiplier = '1' if time_multiplier == None else str(time_multiplier)
            time_unit = 'hour' if time_unit == None else str(time_unit)

            if base_date != None: base_date = datetime.datetime.strptime(base_date, '%Y-%m-%d %H:%M:%S.%f')
            else: base_date = get_eastern_current_time_naive() - datetime.timedelta(hours=1)

            query_params = [base_date, base_date]

            where_sql = "WHERE (coordinate_on between %s and date_add(%s, interval " + time_multiplier + " " + time_unit + "))";
            if uuid != None: 
                uuid = str(uuid)
                where_sql += " and uuid=%s"
                query_params.extend([uuid])

            sql_str = "SELECT uuid, X(coordinate), Y(coordinate), coordinate_on, is_stationary, altitude, speed_mph, heading_degree"
            sql_str += " FROM " + archive_device_tracking_table_name + " " + where_sql + " order by coordinate_on ASC;"

            result = get_device_tracking_archive_query_result_to_array(query_sql(sql_str, query_params))
        else:
            app.application.logger.error('do_get_device_tracking_history: content missing');
    except Exception as e:
        app.application.logger.error('do_get_device_tracking_history: EXCEPTION: ' + str(e));
        result = None
    return result

itpa_video_database_name = 'itpa_video.'

bus_videos_table_name = itpa_video_database_name + 'bus_videos'

sql_insert_new_bus_video = 'INSERT INTO ' + bus_videos_table_name + ' ('
sql_insert_new_bus_video += 'uuid, fleet, bus_id, bus_name, camera_type, has_frame_images, created_on'
sql_insert_new_bus_video += ') VALUES ('
sql_insert_new_bus_video += '%s,%s,%s,%s,%s,%s,%s'
sql_insert_new_bus_video += ');'

sql_update_bus_video_recording_ended = 'UPDATE ' + bus_videos_table_name
sql_update_bus_video_recording_ended += ' SET recording_ended=%s, processing_ended=%s'
sql_update_bus_video_recording_ended += ' WHERE uuid=%s;'

sql_update_bus_video_has_frame_images = 'UPDATE ' + bus_videos_table_name
sql_update_bus_video_has_frame_images += ' SET has_frame_images=%s'
sql_update_bus_video_has_frame_images += ' WHERE uuid=%s;'

sql_select_bus_videos = 'SELECT uuid, fleet, bus_id, bus_name, camera_type, has_frame_images, created_on, recording_ended, processing_ended'
sql_select_bus_videos += ' FROM ' + bus_videos_table_name
sql_select_bus_videos += ' ORDER BY created_on DESC, fleet ASC, bus_name ASC;'

sql_delete_bus_video = 'DELETE FROM ' + bus_videos_table_name + ' WHERE uuid=%s;'

def add_new_bus_video_to_db(request_args):
    status = 400
    try:
        if request_args != None:
            uuid = request_args.get('uuid')
            fleet = request_args.get('bus_fleet')
            bus_id = request_args.get('bus_id')
            bus_name = request_args.get('bus_name')
            camera_type = request_args.get('camera_type')
            created_on = request_args.get('createdOn')
            has_frame_images = request_args.get('hasFrameImages')
            if uuid != None and fleet != None and bus_id != None and bus_name != None and created_on != None:
                if camera_type != None: camera_type = str(camera_type)
                created_on = datetime.datetime.strptime(created_on, '%Y-%m-%dT%H:%M:%S.%fZ')
                created_on = get_eastern_naive_from(created_on)
                has_frame_images = 1 if has_frame_images != False else 0
                insert_record = [str(uuid), str(fleet), str(bus_id), str(bus_name), camera_type, has_frame_images, created_on]
                status = exec_sql_commit_values(sql_insert_new_bus_video, [insert_record])
                if status != None:
                    status = 200
    except Exception as e:
        app.application.logger.error('add_new_bus_video_to_db: EXCEPTION: ' + str(e));
        status = 400
    return status

def end_record_bus_video_to_db(request_args):
    status = 400
    try:
        if request_args != None:
            uuid = request_args.get('uuid')
            recording_ended = request_args.get('recordingEnded')
            processing_ended = request_args.get('processingEnded')
            if uuid != None and recording_ended != None and processing_ended != None:
                recording_ended = datetime.datetime.strptime(recording_ended, '%Y-%m-%dT%H:%M:%S.%fZ')
                recording_ended = get_eastern_naive_from(recording_ended)
                processing_ended = datetime.datetime.strptime(processing_ended, '%Y-%m-%dT%H:%M:%S.%fZ')
                processing_ended = get_eastern_naive_from(processing_ended)
                update_record = [recording_ended, processing_ended, str(uuid)]
                status = exec_sql_commit_values(sql_update_bus_video_recording_ended, [update_record])
                if status != None:
                    status = 200
    except Exception as e:
        app.application.logger.error('end_record_bus_video_to_db: EXCEPTION: ' + str(e));
        status = 400
    return status

def get_bus_videos_from_db_query_result_to_array(records):
    return ([
        {
            'uuid': r[0],
            'fleet': r[1],
            'bus_id': r[2],
            'bus_name': r[3],
            'camera_type': r[4],
            'has_frame_images': r[5] == 1,
            'created_on': get_date_isoformat(r[6]) if r[6] != None else None,
            'recording_ended': get_date_isoformat(r[7]) if r[7] != None else None,
            'processing_ended': get_date_isoformat(r[8]) if r[8] != None else None,
        } for r in records
    ])

def do_get_bus_videos_from_db():
    bus_videos = None
    try:
        bus_videos = query_sql(sql_select_bus_videos)
    except Exception as e:
        bus_videos = None
        app.application.logger.error('get_bus_videos_from_db: EXCEPTION: ' + str(e));
    return bus_videos

def get_bus_videos_from_db():
    return get_bus_videos_from_db_query_result_to_array(do_get_bus_videos_from_db())

SOCKETIO_SERVER = os.environ.get('SOCKETIO_SERVER', 'socketio')
SOCKETIO_PORT = os.environ.get('SOCKETIO_PORT', '1337')
SOCKETIO_TOKEN = os.environ.get('SOCKETIO_TOKEN', '')
SOCKETIO_URL = 'http://' + SOCKETIO_SERVER + ':' + SOCKETIO_PORT + '/'
SOCKETIO_TOKEN = os.environ.get('SOCKETIO_TOKEN', '')

socketIO_del_bus_video = SOCKETIO_URL + 'delete_video'
socketIO_del_bus_video_frames = SOCKETIO_URL + 'delete_video_frames'

def del_bus_video_frames_socket_io(uuid):
    result = False
    try:
        all_url = socketIO_del_bus_video_frames
        r = requests.post(all_url, data = {'token': SOCKETIO_TOKEN, 'uuid': uuid}, timeout=10)
        if r.status_code == 200: result = True
        else: app.application.logger.error('del_bus_video_frames status: ' + str(r.status_code))
    except Exception as e:
        result = False
        app.application.logger.error('del_bus_video_frames exception: ' + str(e));
    return result

def del_bus_video_file_socket_io(uuid):
    result = False
    try:
        all_url = socketIO_del_bus_video
        r = requests.post(all_url, data = {'token': SOCKETIO_TOKEN, 'uuid': uuid}, timeout=10)
        if r.status_code == 200: result = True
        else: app.application.logger.error('del_bus_video_file status: ' + str(r.status_code))
    except Exception as e:
        result = False
        app.application.logger.error('del_bus_video_file exception: ' + str(e));
    return result

def do_del_bus_video(request_args):
    status = 404
    try:
        if request_args != None:
            uuid = request_args.get('uuid')
            if uuid != None:
                del_record = [str(uuid)]
                status = exec_sql_commit_values(sql_delete_bus_video, [del_record])
                if status != None:
                    status = 200
                    del_bus_video_file_socket_io(uuid)
    except Exception as e:
        app.application.logger.error('do_del_bus_video: EXCEPTION: ' + str(e));
        status = 500
    return status

def do_del_bus_video_frames(request_args):
    status = 404
    try:
        if request_args != None:
            uuid = request_args.get('uuid')
            if uuid != None:
                update_record = [0, str(uuid)]
                status = exec_sql_commit_values(sql_update_bus_video_has_frame_images, [update_record])
                if status != None:
                    if del_bus_video_frames_socket_io(uuid):
                        status = 200
    except Exception as e:
        app.application.logger.error('do_del_bus_video_frames: EXCEPTION: ' + str(e));
        status = 500
    return status

def get_congestion_details(request_args):
    result = {}
    try:
        congestion_id = request_args.get('congestion_id') if request_args != None else None
        if congestion_id != None:
            all_url = 'https://fl511.com/tooltip/Congestion/' + str(congestion_id) + '?lang=en-US'
            r = requests.post(all_url, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text)
                table = soup.find('table', attrs={'class':'table-condensed table-striped'})
                table_body = table.find('tbody')
                rows = table_body.find_all('tr')
                loc_td = rows[0].find_all('td')
                location = loc_td[0].text.strip()
                result['location'] = location
                desc_td = rows[1].find_all('td')
                desc = desc_td[0].text.strip()
                result['desc'] = desc
            else: app.application.logger.error('get_congestion_details status: ' + str(r.status_code))
    except Exception as e:
        result = {}
        app.application.logger.error('get_congestion_details exception: ' + str(e));
    return result;
