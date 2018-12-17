import redis
import json
import os
import re
import datetime
import pytz
import requests
from xml.etree import ElementTree

import math
from math import radians, cos, sin, asin, sqrt

import mysql.connector
from mysql.connector import ClientFlag

from celery.utils.log import get_task_logger

global_logger = get_task_logger(__name__)

def get_eastern_naive_from(a_date):
    utc_date = pytz.utc.localize(a_date);
    eastern_tz = pytz.timezone('US/Eastern')
    est_date = utc_date.astimezone(eastern_tz)
    est_date = datetime.datetime(est_date.year, est_date.month, est_date.day, est_date.hour, est_date.minute, est_date.second, est_date.microsecond)
    return est_date

def get_eastern_current_day_only():
    try:
        eastern_tz = pytz.timezone('US/Eastern')
        uct_day_only = datetime.datetime.utcnow()
        uct_day_only = uct_day_only.replace(tzinfo=pytz.utc)
        est_day_only = uct_day_only.astimezone(eastern_tz)
        est_day_only = datetime.datetime(est_day_only.year, est_day_only.month, est_day_only.day, 0, 0, 0)
        return est_day_only
    except Exception as e:
        global_logger.error('get_eastern_current_day_only exception:' + str(e))
    return None

min_lon = -81.7057
max_lon = -80.06966
min_lat = 25.56056
max_lat = 26.5621

def is_in_itpa_extent(lon, lat):
    is_inside = False
    try:
        is_inside = (lon >= min_lon and lon <= max_lon and lat >= min_lat and lat <= max_lat)
    except:
        is_inside= False
    return is_inside

def get_date_isoformat(the_date): return the_date.isoformat() if the_date != None else None

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
        global_logger.error('query_sql exception: ' + str(e));
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
        global_logger.error('exec_sql_commit_values: ' + str(dbError))
    except Exception as cerror:
        global_logger.error('exec_sql_commit_values: ' + str(cerror))
    finally:
        if cursor != None: cursor.close()
        if conn != None: conn.close()
    return ids

def query_delete_stale(sql_select_stale, stale_value, sql_del_by_id):
    fleeds_and_ids_to_del = query_sql(sql_select_stale, stale_value)
    if fleeds_and_ids_to_del != None and len(fleeds_and_ids_to_del) > 0:
        exec_sql_commit_values(sql_del_by_id, fleeds_and_ids_to_del)

def haversine_distance_miles(lon1, lat1, lon2, lat2):
    """
    lon1 = float(lon1)
    lat1 = float(lat1)
    lon2 = float(lon2)
    lat2 = float(lat2)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    r = 3956
    return c * r

def calculate_speed_mph(lat1, lon1, dtime1, lat2, lon2, dtime2, max_seconds_interval):
    distance = haversine_distance_miles(lon1, lat1, lon2, lat2)
    if distance == 0: return 0
    time_in_seconds = abs((dtime1 - dtime2).total_seconds())
    if time_in_seconds == 0 or time_in_seconds > max_seconds_interval: return 0
    speed = float(distance / time_in_seconds)
    speed_mi_hr = round((speed * 3600), 3)
    return speed_mi_hr

def xml_get(element, field_name):
    field = element.find(field_name)
    if field != None:
        if field.text != None: field = field.text.strip()
        else: field = None;
    return field

def filter_html_out(the_text):
    if the_text != None:
        try:
            the_text = re.sub("\r", "", the_text)
            the_text = re.sub("&nbsp;", "", the_text)
            the_text = re.sub("<br />", " ", the_text)
            the_text = re.sub("<br/>", " ", the_text)
            the_text = re.sub(" +", " ", the_text)
        except:
            pass
    return the_text

def get_polygon_from(r):
    polygon = None
    try:
        if r != None and len(r) > 0:
            local_r = r[:]
            local_r = re.sub("[POLYGON|/(|/)]", "", local_r)
            local_r = [x.strip() for x in local_r.split(',') if x != '']
            polygon = []
            poly = []
            for rr in local_r:
                lonlat = rr.split(' ')
                lonlat = [float(lonlat[0]), float(lonlat[1])]
                poly.append(lonlat)
            polygon.append(poly)
    except Exception as e:
        global_logger.error('get_polygon_from: ' + str(e))
        polygon = None
    return polygon

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

def squared_point_distance(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    return dx * dx + dy * dy

def squared_segment_distance(x, y, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx != 0 or dy != 0:
        t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
        if t > 1:
            x1 = x2
            y1 = y2
        elif t > 0: 
            x1 += dx * t
            y1 += dy * t;
    return squared_point_distance(x, y, x1, y1)

def degrees_to_meters(coords):
    lon, lat = coords[0], coords[1]
    x = lon * 20037508.34 / 180.0;
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0);
    y = y * 20037508.34 / 180.0;
    return [x, y]

def LS_simplify(LSCoords, tolerance):
    simplified_coords = []
    squared_tolerance = tolerance * tolerance
    nls_coords = len(LSCoords)
    if nls_coords < 3:
        simplified_coords.extend(LSCoords)
    else:
        markers = [False] * nls_coords
        markers [0] = markers[nls_coords - 1] = True
        stack = [[0, nls_coords - 1]]
        index = 0
        meter_ls_coords = [None] * nls_coords
        for i in range(0, nls_coords):
            meter_ls_coords[i] = degrees_to_meters(LSCoords[i])
        while len(stack) > 0:
            first_last = stack.pop()
            first = first_last[0]
            last = first_last[1]
            x1y1 = meter_ls_coords[first]
            x2y2 = meter_ls_coords[last]
            max_squared_dist = 0.0
            for i in range(first + 1, last):
                xy = meter_ls_coords[i]
                squared_dist = squared_segment_distance(
                    xy[0], xy[1], x1y1[0], x1y1[1], x2y2[0], x2y2[1])
                if squared_dist > max_squared_dist:
                    index = i
                    max_squared_dist = squared_dist
            if max_squared_dist > squared_tolerance:
                markers[index] = True
                if first + 1 < index:
                    stack.append([first, index])
                if index + 1 < nls_coords:
                    stack.append([index, last])
        for i in range(0, nls_coords):
            if markers[i]:
                simplified_coords.append(LSCoords[i])
    return simplified_coords

class MLS_merge(object):
    
    def reset(self):
        self.seg_map = {}
        self.coord_map = {}
        self.segsProcess = {}
        self.ncoords_map = self.nsegs_map = 0
        self.merged_mls = []

    def get_coords_are_different(self, coord1, coord2):
        return (coord1[0] != coord2[0]) or (coord1[1] != coord2[1])

    def get_mins_maxs(self, coord1, coord2):
        if coord1[0] < coord2[0]:
            min_lon = coord1[0]
            max_lon = coord2[0]
        else:
            min_lon = coord2[0]
            max_lon = coord1[0]
        if coord1[1] < coord2[1]:
            min_lat = coord1[1]
            max_lat = coord2[1]
        else:
            min_lat = coord2[1]
            max_lat = coord1[1]
        return min_lon, min_lat, max_lon, max_lat

    def make_coord_key(self, coord):
        return str(coord[0]) + '|' + str(coord[1])

    def add_ls_coord_to_map(self, coord):
        coord_key = self.make_coord_key(coord)
        coord_entry = self.coord_map.get(coord_key)
        if coord_entry == None:
            self.ncoords_map += 1
            coord_entry = self.coord_map[coord_key] = [0, coord_key, coord, 0, {}]
        coord_entry[0] += 1

    def add_ls_coords_to_map(self, LScoords):
        ncoords = len(LScoords)
        for i in range(0, ncoords):
            self.add_ls_coord_to_map(LScoords[i])

    def make_seg_key(self, coord1, coord2):
        min_lon, min_lat, max_lon, max_lat = self.get_mins_maxs(coord1, coord2)
        return self.make_coord_key([min_lon, min_lat]) + '-' + self.make_coord_key([max_lon, max_lat]) 

    def add_seg_to_coord(self, coord_key, seg_key):
        coord_entry = self.coord_map.get(coord_key)
        if coord_entry != None:
            coord_seg_map = coord_entry[4]
            if coord_seg_map.get(seg_key) == None:
                coord_entry[3] += 1
                coord_seg_map[seg_key] = seg_key
            else:
                global_logger.error('adding same segment to coordinate more than once')
        else:
            global_logger.error('adding segment to unmapped coordinate')

    def del_seg_from_coord(self, coord_obj, seg_key):
        if coord_obj[4].get(seg_key) != None:
            del coord_obj[4][seg_key]
            coord_obj[3] -= 1
        else:
            global_logger.error('deleting non existing segment from coordinate')

    def add_ls_seg_to_map(self, coord1, coord2):
        if self.get_coords_are_different(coord1, coord2):
            seg_key = self.make_seg_key(coord1, coord2)
            seg_entry = self.seg_map.get(seg_key)
            if seg_entry == None:
                coord1K = self.make_coord_key(coord1)
                coord2K = self.make_coord_key(coord2)
                self.nsegs_map += 1
                seg_entry = self.seg_map[seg_key] = [0, seg_key, coord1, coord2, coord1K, coord2K]
                self.add_seg_to_coord(coord1K, seg_key)
                self.add_seg_to_coord(coord2K, seg_key)
                self.segsProcess[seg_key] = seg_entry
            seg_entry[0] += 1

    def add_ls_segs_to_map(self, LScoords):
        nsegs = len(LScoords) - 1
        for i in range(0, nsegs):
            self.add_ls_seg_to_map(LScoords[i], LScoords[i + 1])

    def del_seg_to_process(self, seg_key):
        if self.segsProcess.get(seg_key) != None:
            del self.segsProcess[seg_key]
            self.nsegs_process -= 1
        else:
            global_logger.error('deleting invalid segment key from segments to process')

    def get_process_seg_with_max_count(self):
        max_count = 0
        max_seg_obj = None
        for seg_key in self.segsProcess:
            seg_obj = self.segsProcess.get(seg_key)
            seg_count = seg_obj[0]
            if seg_count > max_count:
                max_count = seg_count
                max_seg_obj = seg_obj
        return max_seg_obj

    def get_next_seg_to_process(self):
        next_seg_obj = self.get_process_seg_with_max_count()
        if next_seg_obj != None:
            self.del_seg_to_process(next_seg_obj[1])
        return next_seg_obj

    def remove_first_seg_key_from_coord_obj(self, coord_obj):
        first_seg_key = None
        nsegs = coord_obj[3]
        if nsegs > 0:
            for seg_key in coord_obj[4]:
                first_seg_key = coord_obj[4][seg_key]
                del coord_obj[4][seg_key]
                coord_obj[3] -= 1
                break
        return first_seg_key
    
    def get_other_coord_obj(self, seg_obj, coord_obj):
        other_coord_obj = None
        if seg_obj != None and coord_obj != None:
            coord_key = coord_obj[1]
            if seg_obj[4] == coord_key:
                other_coord_obj = self.coord_map.get(seg_obj[5])
            elif seg_obj[5] == coord_key:
                other_coord_obj = self.coord_map.get(seg_obj[4])
        return other_coord_obj
    
    def continue_ls(self, the_ls, add_to_end):
        continued = False
        the_ls_len = len(the_ls)
        coord_in_ls_index = the_ls_len - 1 if add_to_end else 0
        index_insert_ls = the_ls_len if add_to_end else 0
        coord_in_ls = the_ls[coord_in_ls_index]
        coord_in_lsK = self.make_coord_key(coord_in_ls)
        coord_in_ls_obj = self.coord_map.get(coord_in_lsK)
        if coord_in_ls_obj != None:
            if coord_in_ls_obj[3] > 0:
                next_seg_key = self.remove_first_seg_key_from_coord_obj(coord_in_ls_obj)
                next_seg = self.segsProcess.get(next_seg_key)
                if next_seg != None:
                    other_coord_obj = self.get_other_coord_obj(next_seg, coord_in_ls_obj)
                    if other_coord_obj != None:
                        self.del_seg_to_process(next_seg_key)
                        self.del_seg_from_coord(other_coord_obj, next_seg_key)
                        the_ls.insert(index_insert_ls, other_coord_obj[2])
                        continued = True
                    else:
                        global_logger.error('cannot find other coordinate in segment to process')
                else:
                    global_logger.error('cannot find coordinate segment to process')
        else:
            global_logger.error('cannot find linestring coordinate object to add to')
        
        return continued

    def create_new_ls(self):
        created = False
        if self.nsegs_process > 0:
            next_seg_obj = self.get_next_seg_to_process()
            if next_seg_obj != None:
                seg_key, coord1K, coord2K = next_seg_obj[1], next_seg_obj[4], next_seg_obj[5]
                coord1_obj = self.coord_map.get(coord1K)
                coord2_obj = self.coord_map.get(coord2K)
                if coord1_obj != None and coord2_obj != None:
                    new_ls = []
                    self.merged_mls.append(new_ls)
                    self.del_seg_from_coord(coord1_obj, seg_key)
                    self.del_seg_from_coord(coord2_obj, seg_key)
                    new_ls.append(coord1_obj[2])
                    new_ls.append(coord2_obj[2])
                    while self.continue_ls(new_ls, True):
                        continue
                    while self.continue_ls(new_ls, False):
                        continue
                    created = True
                else:
                    global_logger.error('segment with missing coordinates detected')
            else:
                global_logger.error('cannot find a next segment object to process')
        return created

    def merge(self, MLS):
        self.reset()
        nLS = len(MLS)
        for i in range(0, nLS):
            self.add_ls_coords_to_map(MLS[i])
        for i in range(0, nLS):
            self.add_ls_segs_to_map(MLS[i])
        self.nsegs_process = self.nsegs_map
        while self.create_new_ls() == True:
            continue
        return self.merged_mls

def get_data_from_url(url, title, headers = None, timeout = 2):
    data = None
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        global_logger.error(title + ' exception: ' + str(e))
        data = None
    return data

def get_xml_data_from_url(url, title, headers = None, timeout = 2, use_decode = False):
    data = None
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        if use_decode:
            r.raw.decode_content = True
        data = ElementTree.fromstring(r.content)
    except Exception as e:
        global_logger.error(title + ' exception: ' + str(e))
        data = None
    return data
