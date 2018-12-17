import time
import logging
import requests
import os
from xml.etree import ElementTree
import datetime
import pytz

from bs4 import BeautifulSoup

from celery.utils.log import get_task_logger

from redisjson import (redis_load, redis_set, ejson_loads, ejson_dumps)

from utils import (is_in_itpa_extent, filter_html_out, xml_get, calculate_speed_mph,
    CompressCodec, LS_simplify, MLS_merge, get_eastern_current_day_only,
    get_data_from_url,
    get_xml_data_from_url,
    )

global_logger = get_task_logger(__name__)

"""
[{
    "itemId":"District 5--880489",
    "location":[28.38174,-81.49915],
    "zindex":25,
    "icon":{
        "url":"/Content/Images/map_queue.png",
        "size":[25,35],
        "origin":[0,0],
        "anchor":[12,34]},
        "title":""
    },
}
"""

def get_congestion_details(congestion_id):
    result = {}
    try:
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
            else: global_logger.error('get_congestion_details status: ' + str(r.status_code))
    except Exception as e:
        result = {}
        global_logger.error('get_congestion_details exception: ' + str(e));
    return result;

def load_fl511_congestions_from_fl511():
    records = None
    had_exception = ''
    try:
        r = requests.get("https://fl511.com/map/mapIcons/Congestion", timeout=10)
        if r.status_code == 200:
            result = r.json()
            if result != None:
                records = []
                for msgboard in result:
                    try:
                        id = msgboard.get("itemId")
                        location = msgboard.get("location")
                        if (id != None and location != None):
                            id = id.strip()
                            lon = location[1]
                            lat = location[0]
                            if is_in_itpa_extent(lon, lat):
                                details = get_congestion_details(id)
                                location = details.get('location')
                                desc = details.get('desc')
                                records.append([id, lon, lat, location, desc])
                    except Exception as e:
                        if len(had_exception) == 0: had_exception = str(e)
        else:
            global_logger.error('load_fl511_congestions_from_fl511: request status code' + str(r.status_code))
    except Exception as e:
        global_logger.error('load_fl511_congestions_from_fl511 exception: ' + str(e))
        records = None
    if len(had_exception) > 0: global_logger.error('load_fl511_congestions_from_fl511 had exception in loop: ' + had_exception)
    return records

"""
{
    "itemId":"1zcct330v0h--1",
    "location":[30.175272,-85.660558],
    "zindex":1,
    "icon":{
        "url":"/Content/Images/map_camera.png",
        "size":[25,35],
        "origin":[0,0],
        "anchor":[12,34]},
        "title":""
    }
}
"""

def load_fl511_cameras_from_fl511():
    records = None
    had_exception = ''
    try:
        r = requests.get("https://fl511.com/map/mapIcons/Cameras", timeout=10)
        if r.status_code == 200:
            result = r.json()
            if result != None:
                records = []
                for msgboard in result:
                    try:
                        id = msgboard.get("itemId")
                        location = msgboard.get("location")
                        if (id != None and location != None):
                            id = id.strip()
                            lon = location[1]
                            lat = location[0]
                            if is_in_itpa_extent(lon, lat):
                                records.append([id, lon, lat])
                    except Exception as e:
                        if len(had_exception) == 0: had_exception = str(e)
        else:
            global_logger.error('load_fl511_cameras_from_fl511: request status code' + str(r.status_code))
    except Exception as e:
        global_logger.error('load_fl511_cameras_from_fl511 exception: ' + str(e))
        records = None
    if len(had_exception) > 0: global_logger.error('load_fl511_cameras_from_fl511 had exception in loop: ' + had_exception)
    return records

"""
{
  "itemId": "231--District 5",
  "location": [28.058044, -80.691661],
  "zindex": 1,
  "icon": {
    "url": "/Content/Images/map_messageSign.png",
    "size": [25, 35],
    "origin": [0, 0],
    "anchor": [12, 34]
  },
  "title": ""
}
"""
def load_fl511_message_boards_from_fl511():
    message_boards = None
    had_exception = ''
    try:
        r = requests.get("https://fl511.com/map/mapIcons/MessageSigns", timeout=10)
        if r.status_code == 200:
            result = r.json()
            if result != None:
                message_boards = []
                for msgboard in result:
                    try:
                        board_id = msgboard.get("itemId")
                        board_location = msgboard.get("location")
                        if (board_id != None and board_location != None):
                            board_id = board_id.strip()
                            board_lon = board_location[1]
                            board_lat = board_location[0]
                            if is_in_itpa_extent(board_lon, board_lat):
                                message_boards.append([board_id, board_lon, board_lat])
                    except Exception as e:
                        if len(had_exception) == 0: had_exception = str(e)
        else:
            global_logger.error('load_fl511_message_boards_from_fl511: request status code' + str(r.status_code))
    except Exception as e:
        global_logger.error('load_fl511_message_boards_from_fl511 exception: ' + str(e))
        message_boards = None
    if len(had_exception) > 0: global_logger.error('load_fl511_message_boards_from_fl511 had exception in loop: ' + had_exception)
    return message_boards

"""
{"draw":1,"recordsTotal":727,"recordsFiltered":727,"data":[{"DT_RowId":"10--CFX","tooltipUrl":"/tooltip/MessageSigns/10--CFX?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-408","direction":"E","name":"SR-408 EB at Mills Ave","message":"TRAVEL TIME TO<br/>SR 436 EXIT UNDER 3 MIN<br/>SR 417 6-8 MIN","message2":"","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"101--District 5","tooltipUrl":"/tooltip/MessageSigns/101--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-95","direction":"N","name":"I-95 NB at MM 199.5","message":"SR 528<br/>6 MILES<br/>6 MIN","message2":"SR 524<br/>3 MILES<br/>3 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Brevard"},{"DT_RowId":"102--District 5","tooltipUrl":"/tooltip/MessageSigns/102--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-95","direction":"S","name":"I-95 SB at MM 203.8","message":"SR 519<br/>8 MILES<br/>7 MIN","message2":"CR 509<br/>12 MILES<br/>11 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Brevard"},{"DT_RowId":"103--District 5","tooltipUrl":"/tooltip/MessageSigns/103--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-95","direction":"N","name":"I-95 NB at MM 203.8","message":"SR 407<br/>8 MILES<br/>8 MIN","message2":"SR 50<br/>11 MILES<br/>10 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Brevard"},{"DT_RowId":"105--District 5","tooltipUrl":"/tooltip/MessageSigns/105--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-528","direction":"W","name":"SR-528 WB E of I-95","message":"I-95 NORTH TO<br/>I-4<br/>37 MILES 32 MIN","message2":"I-95 SOUTH TO<br/>US 192<br/>20 MILES 18 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Brevard"},{"DT_RowId":"106--District 5","tooltipUrl":"/tooltip/MessageSigns/106--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-95","direction":"S","name":"I-95 SB at MM 206.4","message":"SR 520<br/>5 MILES<br/>5 MIN","message2":"SR 519<br/>11 MILES<br/>10 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Brevard"},{"DT_RowId":"107--District 5","tooltipUrl":"/tooltip/MessageSigns/107--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB at Par St","message":"CONGESTION<br/>AHEAD<br/>3 MILES","message2":"SR 528<br/>14 MILES<br/>15 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"108--District 5","tooltipUrl":"/tooltip/MessageSigns/108--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"E","name":"I-4 EB E of Lee Rd","message":"LAKE MARY BLVD<br/>9 MILES<br/>9 MIN","message2":"ST JOHNS BRIDGE<br/>16 MILES<br/>16 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"11--CFX","tooltipUrl":"/tooltip/MessageSigns/11--CFX?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-408","direction":"E","name":"SR-408 EB at Goldenrod Rd","message":"TRAVEL TIME TO<br/>ALOMA VIA 417N 6-8 MIN<br/>SR 528 VIA 417S 8-10 MIN","message2":"","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"111--District 5","tooltipUrl":"/tooltip/MessageSigns/111--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB E of SR-434","message":"CONGESTION<br/>NEXT<br/>7 MILES","message2":"SR 50<br/>11 MILES<br/>14 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Seminole"},{"DT_RowId":"112--District 5","tooltipUrl":"/tooltip/MessageSigns/112--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB E of Lake Mary Blvd","message":"DON'T DRINK<br/>AND DRIVE<br/>ARRIVE ALIVE","message2":"SR 436<br/>8 MILES<br/>10 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Seminole"},{"DT_RowId":"116--District 5","tooltipUrl":"/tooltip/MessageSigns/116--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"E","name":"I-4 EB W of Dirksen Rd","message":"SR 44<br/>11 MILES<br/>10 MIN","message2":"I-95<br/>25 MILES<br/>22 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Volusia"},{"DT_RowId":"117--District 5","tooltipUrl":"/tooltip/MessageSigns/117--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB at Enterprise Rd","message":"DON'T DRINK<br/>AND DRIVE<br/>ARRIVE ALIVE","message2":"SR 417<br/>7 MILES<br/>7 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Volusia"},{"DT_RowId":"118--District 5","tooltipUrl":"/tooltip/MessageSigns/118--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB E of SR-472","message":"SR 417<br/>12 MILES<br/>11 MIN","message2":"SR 50<br/>30 MILES<br/>33 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Volusia"},{"DT_RowId":"12--CFX","tooltipUrl":"/tooltip/MessageSigns/12--CFX?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-408","direction":"E","name":"SR-408 EB at Alafaya Trl","message":"TRAVEL TIME TO<br/>EAST COLONIAL DR<br/> LESS THAN 3 MIN","message2":"","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"121--District 5","tooltipUrl":"/tooltip/MessageSigns/121--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"E","name":"I-4 EB at Ivanhoe Blvd","message":"DON'T DRINK<br/>AND DRIVE<br/>ARRIVE ALIVE","message2":"LAKE MARY BLVD<br/>13 MILES<br/>14 MIN","lastUpdated":"7/27/18, 8:54 AM","county":"Orange"},{"DT_RowId":"122--District 5","tooltipUrl":"/tooltip/MessageSigns/122--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB at Kaley St","message":"FL TURNPIKE<br/>5 MILES<br/>6 MIN","message2":"SR 528<br/>9 MILES<br/>10 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"123--District 5","tooltipUrl":"/tooltip/MessageSigns/123--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"E","name":"I-4 EB at Michigan St","message":"CONGESTION<br/>NEXT<br/>3 MILES","message2":"SR 436<br/>10 MILES<br/>13 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"124--District 5","tooltipUrl":"/tooltip/MessageSigns/124--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB W of OBT","message":"DON'T DRINK<br/>AND DRIVE<br/>ARRIVE ALIVE","message2":"US 192<br/>15 MILES<br/>15 MIN","lastUpdated":"7/27/18, 8:52 AM","county":"Orange"},{"DT_RowId":"126--District 5","tooltipUrl":"/tooltip/MessageSigns/126--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"W","name":"I-4 WB W of Conroy Rd","message":"SR 528<br/>5 MILES<br/>5 MIN","message2":"US 192<br/>12 MILES<br/>12 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"126--CFX","tooltipUrl":"/tooltip/MessageSigns/126--CFX?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-429","direction":"N","name":"SR-429 NB N. of Lust Rd","message":"TRAVEL TIME TOKELLY PARK RD 4-6 MINVIA8-10 MIN","message2":"","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"127--District 5","tooltipUrl":"/tooltip/MessageSigns/127--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"E","name":"I-4 EB E of SR-528","message":"DON'T DRINK<br/>AND DRIVE<br/>ARRIVE ALIVE","message2":"SR 50<br/>11 MILES<br/>14 MIN","lastUpdated":"7/27/18, 8:51 AM","county":"Orange"},{"DT_RowId":"127--CFX","tooltipUrl":"/tooltip/MessageSigns/127--CFX?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-429","direction":"S","name":"SR 429 SB N of Ponkan","message":"ALL LANES BLOCKED<br/>AHEAD 7 MILES<br/>AT EXIT 29 OCOEE APOPKA","message2":"USE EXIT 30/SR-414<br/>TO US 441 SB<br/>AS ALTERNATE","lastUpdated":"7/27/18, 8:22 AM","county":"Orange"},{"DT_RowId":"128--District 5","tooltipUrl":"/tooltip/MessageSigns/128--District 5?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"I-4","direction":"E","name":"I-4 EB E of SR-535","message":"FL TURNPIKE<br/>7 MILES<br/>9 MIN","message2":"SR 50<br/>15 MILES<br/>19 MIN","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"},{"DT_RowId":"128--CFX","tooltipUrl":"/tooltip/MessageSigns/128--CFX?lang=%7Blang%7D&noCss=true","region":"Central","roadwayName":"SR-429","direction":"N","name":"SR-429 NB N. of Ponkan Rd","message":"TRAVEL TIME TOVIA5-7 MIN","message2":"","lastUpdated":"7/27/18, 8:56 AM","county":"Orange"}]}
"""

def load_fl511_messages_from_fl511():
    messages = None
    had_exception = ''
    try:
        form_data = { "length": 1000 }
        r = requests.post("https://fl511.com/List/GetData/MessageSigns", timeout=10, data=form_data)
        if r.status_code == 200:
            #global_logger.error('WILL TRY TO READ JSON ' + str(r.status_code) + ' ' + r.text)
            result = r.json()
            data = result.get('data') if result != None else None
            if data != None:
                messages = []
                for msg in data:
                    try:
                        board_id = msg.get("DT_RowId")
                        last_message = msg.get("message")
                        last_message2 = msg.get("message2")
                        last_message_on = msg.get("lastUpdated")
                        highway = msg.get("roadwayName")
                        region = msg.get("region")
                        location = msg.get("name")
                    
                        if (board_id == None or last_message == None or  
                            last_message_on == None or highway == None or 
                            location == None or region == None):
                            global_logger.warning('load_fl511_messages_from_fl511: message with incomplete format')
                            continue

                        board_id = board_id.strip()
                        last_message = filter_html_out(last_message.strip())

                        if last_message2 != None and len(last_message2) > 0:
                            last_message2 = filter_html_out(last_message2.strip())
                            last_message += ' - ' + last_message2

                        highway = highway.strip()
                        region = region.strip()
                        location = location.strip()

                        last_message_on = last_message_on.strip()
                        last_message_on = datetime.datetime.strptime(last_message_on, "%m/%d/%y, %I:%M %p") 

                        messages.append([board_id, last_message, highway, region, last_message_on, location])
                    except Exception as e:
                        if len(had_exception) == 0: had_exception = str(e)
        else:
            global_logger.error('load_fl511_messages_from_fl511: request status code' + str(r.status_code))
    except Exception as e:
        global_logger.error('load_fl511_messages_from_fl511 exception : ' + str(e))
        messages = None
    if len(had_exception) > 0: global_logger.error('load_fl511_messages_from_fl511 had exception in loop: ' + had_exception)
    return messages

# Florida Highway Safety and Motor Vehicles
flhsmv_url = "http://gis.flhsmv.gov/arcgisfhptrafficsite/rest/services/Traffic_Feed/MapServer/0/query?f=json&where=1%3D1&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry%3D%7B%22xmin%22%3A-81.7057%2C%22ymin%22%3A25.56056%2C%22xmax%22%3A-80.06966%2C%22ymax%22%3A26.5621%2C%22spatialReference%22%3A%7B%22wkid%22%3A3857%7D%7D&geometryType=esriGeometryEnvelope&inSR=102100&outFields=OBJECTID%2CTYPEEVENT%2CDISPATCHCENTER%2CLOCATION%2CREMARKS%2CINCIDENTID%2CDATE%2CTIME%2CLAT%2CLON%2CCOUNTY&orderByFields=OBJECTID%20ASC&outSR=102100"
def load_flhsmv_incidents_from_flhsmv():
    incidents = None
    had_exception = ''
    try:
        r = requests.get(flhsmv_url, timeout=10)
        result = r.json()
        features = result.get('features') if result != None else None
        if features != None:
            incidents = []
            for feature in features:
                try:
                    attributes = feature.get('attributes');
                    if attributes != None:
                        inc_id = attributes.get("INCIDENTID")
                        inc_type = attributes.get("TYPEEVENT")
                        inc_date = attributes.get("DATE")
                        inc_lon = attributes.get("LON")
                        inc_lat = attributes.get("LAT")
                        inc_location = attributes.get("LOCATION")
                        inc_county = attributes.get("COUNTY")
                        inc_remarks = attributes.get("REMARKS")
                        inc_time = attributes.get("TIME")
                        if (inc_id != None and inc_type != None and inc_date != None and 
                            inc_lon != None and inc_lat != None and is_in_itpa_extent(inc_lon, inc_lat)):
                            if inc_time == None:
                                inc_time = "00:00"
                            if inc_location != None:
                                inc_location = filter_html_out(inc_location.strip())
                            inc_datetime = "%s" % (datetime.datetime.strptime("%s %s" % (inc_date, inc_time), "%Y/%m/%d %H:%M"))
                            incidents.append([inc_id, inc_type, inc_datetime, inc_lon, inc_lat, inc_location, inc_county, inc_remarks])
                except Exception as e:
                    if len(had_exception) == 0: had_exception = str(e)
    except Exception as e:
        global_logger.error('load_flhsmv_incidents_from_fl511: ' + str(e))
        incidents = None
    if len(had_exception) > 0:
        global_logger.error('load_flhsmv_incidents_from_fl511 had exception in loop: ' + had_exception)
    return incidents

#BUS POSITIONS

mdt_bus_route_ids = [7, 8, 11, 24, 34, 36, 51, 71, 95, 137, 150, 200, 212, 238, 288, 297, 301, 302]
mdt_bus_route_id_maps = { str(route_id):str(route_id) for route_id in mdt_bus_route_ids }
#mdt_bus_route_ids_str = ','.join(str(s) for s in mdt_bus_route_ids)

mdt_heading_dict = {'N' : 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315 }

max_seconds_interval_for_speed = 4 * 60

mdt_bus_url = "http://www.miamidade.gov/transit/WebServices/Buses/?BusID="
mdt_last_bus_info_redis_key = 'mdt_last_bus_info'

def load_mdt_buses_from_mdt():
    #global mdt_last_bus_info
    current_buses = None
    archive_buses = None
    new_last_bus_info = {}
    cur_bus_info = redis_load(mdt_last_bus_info_redis_key)
    if cur_bus_info == None: cur_bus_info = {}
    had_exception = ''
    try:
        r = requests.get(mdt_bus_url, timeout=10)
        current_bus_elements = ElementTree.fromstring(r.content)
        current_buses = []
        archive_buses= []
        now_time = datetime.datetime.now()
        now_time_str = str(now_time.date())
        fleet = 'mdt'
        occupancy_percentage = None
        for cb in current_bus_elements:
            try:
                route_id = xml_get(cb, "RouteID")
                if mdt_bus_route_id_maps.get(route_id) != None:
                    bus_id = xml_get(cb, "BusID")
                    bus_name = xml_get(cb, 'BusName')
                    latitude_str = xml_get(cb, "Latitude")
                    longitude_str = xml_get(cb, "Longitude")
                    trip_id = xml_get(cb, "TripID")
                    direction = xml_get(cb, "ServiceDirection")
                    heading = xml_get(cb, "Direction")
                    date_updated_text = xml_get(cb, "LocationUpdated")
                        
                    if bus_id == None and bus_name != None: bus_id = bus_name
                    elif bus_name == None and bus_id != None: bus_name = bus_id

                    if bus_id == None or bus_name == None or latitude_str == None or longitude_str == None or heading == None or date_updated_text == None:
                        continue

                    heading_number = mdt_heading_dict.get(heading)
                    heading = heading_number if heading_number != None else 0
                        
                    latitude = float(latitude_str)
                    longitude = float(longitude_str)

                    date_updated = datetime.datetime.strptime("%s %s" % (now_time_str, date_updated_text), "%Y-%m-%d %I:%M:%S %p")

                    speed_mph = 0

                    last_bus_info = cur_bus_info.get(bus_id)

                    add_to_archive = True

                    if last_bus_info != None:
                        last_longitude, last_latitude, last_date_updated, speed_mph = last_bus_info
                        if last_date_updated > date_updated: continue
                    
                        if last_date_updated != date_updated:
                            speed_mph = calculate_speed_mph(
                                last_latitude, last_longitude, last_date_updated, 
                                latitude, longitude, date_updated, 
                                max_seconds_interval_for_speed)
                        else:
                            add_to_archive = False

                    current_bus_record = [
                        fleet, bus_id, bus_name, route_id, direction, trip_id, longitude, latitude, date_updated, occupancy_percentage, speed_mph, heading
                    ]

                    current_buses.append(current_bus_record)

                    if add_to_archive: archive_buses.append(current_bus_record[:])

                    new_last_bus_info[bus_id] = (longitude, latitude, date_updated, speed_mph)
            except Exception as e: 
                if len(had_exception) == 0: had_exception = str(e)
        redis_set(mdt_last_bus_info_redis_key, new_last_bus_info)
    except Exception as e:
        global_logger.error('load_mdt_buses_from_mdt: ' + str(e))
        archive_buses = current_buses = None
    if len(had_exception) > 0:
        global_logger.error('load_mdt_buses_from_mdt had exception in loop: ' + had_exception)

    return current_buses, archive_buses

transloc_id_for_FIU = '571'
transloc_current_bus_service_url = "https://transloc-api-1-2.p.mashape.com/vehicles.json?agencies=" + transloc_id_for_FIU
transloc_current_bus_service_url_headers = {"X-Mashape-Key": "nBnzIRw8T3mshZQA3b89Xx64SMpAp1JitP7jsnJP0E7Gc9J4We"}

fiu_last_bus_info_redis_key = 'fiu_last_bus_info'

def load_fiu_buses_from_transloc():
    current_buses = None
    archive_buses = None
    bus_etas = None
    new_last_bus_info = {}
    cur_bus_info = redis_load(fiu_last_bus_info_redis_key)
    if cur_bus_info == None: cur_bus_info = {}
    try:
        r = requests.get(transloc_current_bus_service_url, timeout=10, headers=transloc_current_bus_service_url_headers)
        result = r.json()
        data = None
        if result != None:
            transloc_data = result.get('data')
            if transloc_data != None:
                data = transloc_data.get(transloc_id_for_FIU)
            if data != None:
                fleet = 'fiu'
                direction = 'Loop'
                trip_id = -1
                now_time0 = datetime.datetime.utcnow()
                now_time_utc = now_time0.replace(tzinfo=pytz.utc)
                eastern_tz = pytz.timezone('US/Eastern')
                current_buses = []
                archive_buses = []
                bus_etas = []
                eta_exception = None
                eta_map = {}
                for d in data:
                    tracking_status = d.get('tracking_status')
                    location = d.get('location')

                    if location is None or tracking_status != 'up': continue

                    bus_id = d.get('vehicle_id')
                    bus_name = d.get('call_name')
                    route_id = d.get('route_id')
                    longitude = location.get('lng')
                    latitude = location.get('lat')
                    last_update = d.get('last_updated_on')

                    if (bus_id == None or bus_name == None or route_id == None or 
                        longitude == None or latitude == None or last_update == None): continue

                    utc_date0 = datetime.datetime.strptime(last_update[:-6], '%Y-%m-%dT%H:%M:%S')
                    utc_date = pytz.utc.localize(utc_date0);

                    date_diff = now_time_utc - utc_date
                    date_diff_days = date_diff.days

                    if date_diff_days > 1: continue

                    est_date = utc_date.astimezone(eastern_tz)
                    est_date = datetime.datetime(est_date.year, est_date.month, est_date.day, est_date.hour, est_date.minute, est_date.second)

                    bus_id = str(bus_id)

                    longitude = float(longitude)
                    latitude = float(latitude)

                    speed_kmh = d.get('speed')
                    heading = d.get('heading')

                    speed_mph = speed_kmh * 0.621371192 if speed_kmh != None else 0
                    if heading == None: heading = 0

                    occupancy_percentage = d.get('passenger_load')

                    if occupancy_percentage != None:
                        occupancy_percentage = 0 if occupancy_percentage < 0 else 1 if occupancy_percentage > 1 else occupancy_percentage

                    add_to_archive = True
                    last_bus_info = cur_bus_info.get(bus_id)

                    if last_bus_info != None:
                        if last_bus_info[2] > est_date: continue
                        add_to_archive = (last_bus_info[0] != longitude or last_bus_info[1] != latitude) and last_bus_info[2] != est_date

                    current_bus_record = [
                        fleet, bus_id, bus_name, route_id, direction, trip_id, longitude, latitude, est_date, occupancy_percentage, speed_mph, heading
                    ]

                    current_buses.append(current_bus_record)

                    if add_to_archive: archive_buses.append(current_bus_record[:])

                    new_last_bus_info[bus_id] = [longitude, latitude, est_date]

                    try:
                        arrival_estimates = d.get('arrival_estimates')
                        if arrival_estimates != None:
                            for ae in arrival_estimates:
                                ae_stop_id = ae.get('stop_id')
                                ae_arrival_at = ae.get('arrival_at')
                                if ae_stop_id != None and ae_arrival_at != None:
                                    ae_stop_id = str(ae_stop_id)
                                    eta_key = bus_id + '|' + ae_stop_id
                                    if eta_map.get(eta_key) == None:
                                        eta_map[eta_key] = True
                                        est_eta = datetime.datetime.strptime(ae_arrival_at[:-6], '%Y-%m-%dT%H:%M:%S')
                                        #fleet, bus_id, stop_id, route_id, est_stop_eta
                                        eta_record = [fleet, bus_id, ae_stop_id, route_id, est_eta]
                                        bus_etas.append(eta_record)
                    except Exception as e: eta_exception = e

                redis_set(fiu_last_bus_info_redis_key, new_last_bus_info)

                if eta_exception != None:
                    global_logger.error('load_fiu_buses_from_transloc ETA exception: ' + str(eta_exception))
        else:
            global_logger.error('load_fiu_buses_from_transloc: transloc API returned null')
    except Exception as e:
        global_logger.error('load_fiu_buses_from_transloc: ' + str(e))
        archive_buses = current_buses = bus_etas = None

    return current_buses, archive_buses, bus_etas

utma_transit_server = "http://transit.cs.fiu.edu/api/v1/transit/"
#utma_transit_server = "http://192.168.0.105:8080/v1/transit/"
#utma_transit_server = "http://192.168.0.81/api/v1/transit/"

utma_transit_server_bus_tracking_url = utma_transit_server + "gettrack"
utma_last_bus_info = {}

utma_bus_name_by_id = {
    '5012' : 'MPV-1',
    '0' : 'MPV-2',
    '5011' : 'MPV-3',
    '5667' : 'SW-1',
    '7140' : 'SW-2',
    '8828' : 'SW-3',
    '1103' : 'SW-4',
    '4056' : 'SW-5',
    '4061' : 'SW-6',
    '25001' : 'SW-7',
}

utma_last_bus_info_redis_key = 'utma_last_bus_info'

def load_utma_buses_from_transit_server():
    current_buses = None
    archive_buses = None
    new_last_bus_info = {}
    cur_bus_info = redis_load(utma_last_bus_info_redis_key)
    if cur_bus_info == None: cur_bus_info = {}
    try:
        r = requests.get(utma_transit_server_bus_tracking_url, timeout=10)
        data = r.json()
        if data != None:
            fleet = 'utma'
            direction = 'Loop'
            trip_id = -1
            current_buses = []
            archive_buses = []
            occupancy_percentage = None
            for bus_read in data:
                bus_id = bus_read.get("id")
                bus_name = utma_bus_name_by_id.get(str(bus_id)) if bus_id != None else None
                latitude_str = bus_read.get("lat")
                longitude_str = bus_read.get("lon")
                heading = bus_read.get("heading")
                date_updated_text = bus_read.get("date")
                speed_mph = bus_read.get("speed")

                if (bus_id == None or bus_name == None or latitude_str == None or longitude_str == None or 
                    heading == None or date_updated_text == None or speed_mph == None):
                    has_format_error = True
                    continue
                    
                bus_id = str(bus_id)
                latitude = float(latitude_str)
                longitude = float(longitude_str)
                speed_mph = float(speed_mph)
                heading = int(heading)

                date_updated = datetime.datetime.strptime(date_updated_text, '%Y-%m-%d %H:%M:%S.%f')

                add_to_archive = True
                last_bus_info = cur_bus_info.get(bus_id)

                if last_bus_info != None:
                    if last_bus_info[2] > date_updated: continue
                    add_to_archive = (last_bus_info[0] != longitude or last_bus_info[1] != latitude) and last_bus_info[2] != date_updated

                route_id = 2 if bus_name.find('SW') == -1 else 1

                current_bus_record = [
                    fleet, bus_id, bus_name, route_id, direction, trip_id, longitude, latitude, date_updated, occupancy_percentage, speed_mph, heading
                ]

                current_buses.append(current_bus_record)

                if add_to_archive: archive_buses.append(current_bus_record[:])

                new_last_bus_info[bus_id] = [longitude, latitude, date_updated]

            redis_set(utma_last_bus_info_redis_key, new_last_bus_info)
        else:
            global_logger.error('load_utma_buses_from_transit_server: transit server returned null')
    except Exception as e:
        global_logger.error('load_utma_buses_from_transit_server: ' + str(e))
        archive_buses = current_buses = None

    return current_buses, archive_buses

#BUS STOPS

utma_transit_server_bus_stops = utma_transit_server + "stops?agency="
utma_transit_server_bus_stops_for_itpa_mdt_routes_redis_key = 'utma_transit_server_bus_stops_for_itpa_mdt_routes'

def process_bus_stops_from_transit_server(fleet, data):
    if data != None:
        bus_stops = []
        for d in data:
            stop_id = d.get('id_in_agency')
            code = d.get('code')
            name = d.get('name')
            desc = d.get('desc')
            lon = d.get('lon')
            lat = d.get('lat')
            if stop_id == None or code == None or name == None or lon == None or lat == None: continue
            record = [fleet, stop_id, code, name, desc, lon, lat]
            bus_stops.append(record)
    else:
        global_logger.error('process_bus_stops_from_transit_server: transit server returned null for fleet: ' + fleet)
    return bus_stops

def get_bus_stops_from_transit_server(url, fleet):
    bus_stops = None
    if url != None:
        try:
            all_url = url + fleet.upper()
            #global_logger.info('get_bus_stops_from_transit_server fleet: ' + fleet + ' all_url: ' + all_url)
            r = requests.get(all_url, timeout=10)
            bus_stops = process_bus_stops_from_transit_server(fleet, r.json())
        except Exception as e:
            global_logger.error('get_mdt_bus_stops_from_transit_server fleet: ' + fleet + ': ' + str(e))
            bus_stops = None
    return bus_stops

def get_mdt_bus_stops_from_transit_server(): 
    return get_bus_stops_from_transit_server(redis_load(utma_transit_server_bus_stops_for_itpa_mdt_routes_redis_key), 'mdt')

def get_utma_bus_stops_from_transit_server(): return get_bus_stops_from_transit_server(utma_transit_server_bus_stops, 'utma')

transloc_stops_service_url = 'http://feeds.transloc.com/stops.json?agencies=' + transloc_id_for_FIU

def get_fiu_bus_stops_from_transloc():
    bus_stops = None
    try:
        r = requests.get(transloc_stops_service_url, timeout=10)
        data = r.json()
        stops = data.get('stops') if data != None else None
        if stops != None:
            fleet = 'fiu'
            desc = None
            bus_stops = []
            for d in stops:
                stop_id = d.get('id')
                code = d.get('code')
                name = d.get('name')
                position = d.get('position')
                lon = position[1] if position != None else None
                lat = position[0] if position != None else None

                if stop_id == None or code == None or name == None or lon == None or lat == None:
                    continue

                record = [
                    fleet, stop_id, code, name, desc, lon, lat
                ]
                bus_stops.append(record)
        else:
            global_logger.error('get_fiu_bus_stops_from_transloc: transloc returned null stops')
    except Exception as e:
        global_logger.error('get_fiu_bus_stops_from_transloc: ' + str(e))
        bus_stops = None

    return bus_stops

#BUS ROUTES

utma_transit_server_bus_routes = utma_transit_server + "routes?stop_ids=true&agency="

def get_bus_routes_from_transit_server(fleet, check_id_map = None):
    global utma_transit_server_bus_stops_for_itpa_mdt_routes
    bus_routes = None
    try:
        r = requests.get(utma_transit_server_bus_routes + fleet.upper(), timeout=10)
        data = r.json()
        if data != None:
            bus_routes = []
            mdt_bus_route_ids = []
            cc = CompressCodec()
            for d in data:
                route_id = d.get('sname') if check_id_map != None else d.get('id')
                if check_id_map == None or check_id_map.get(str(route_id)) != None:
                    transit_route_id = d.get('id')
                    route_name = d.get('lname')
                    color = d.get('color')
                    compressed_multi_linestring = d.get('cmls')
                    ndirections = d.get('ndirs')
                    direction_names = d.get('dir_names')
                    direction_shapes = d.get('dir_shapes')
                    stop_ids = d.get('stop_ids')

                    if (transit_route_id == None or route_id == None or route_name == None or color == None or ndirections == None or 
                        direction_names == None or direction_shapes == None or compressed_multi_linestring == None or
                        stop_ids == None):
                        continue

                    compressed_multi_linestring = ejson_loads(compressed_multi_linestring)
                    direction_shapes = ejson_loads(direction_shapes)

                    compressed_stop_ids = ','.join(str(item.get('id_in_agency')) for item in stop_ids)

                    record = [
                        fleet, route_id, route_name, color, compressed_multi_linestring, ndirections, direction_names, direction_shapes,
                        compressed_stop_ids
                    ]
                    bus_routes.append(record)
                    mdt_bus_route_ids.append(transit_route_id)
            if check_id_map != None:
                mdt_bus_route_ids_str = ','.join(str(s) for s in mdt_bus_route_ids)
                redis_set(utma_transit_server_bus_stops_for_itpa_mdt_routes_redis_key,
                    utma_transit_server + "route_stops/" + mdt_bus_route_ids_str + "?agency=")
        else:
            global_logger.error('get_bus_routes_from_transit_server: transit server returned null fleet: ' + fleet)
    except Exception as e:
        global_logger.error('get_routes_from_transit_server fleet ' + fleet + ':' + str(e))
        bus_routes = None

    return bus_routes

def get_mdt_bus_routes_from_transit_server(): return get_bus_routes_from_transit_server('mdt', mdt_bus_route_id_maps)
def get_utma_bus_routes_from_transit_server(): return get_bus_routes_from_transit_server('utma')

transloc_routes_service_url = 'http://feeds.transloc.com/routes.json?agencies=' + transloc_id_for_FIU
transloc_route_segments_service_url = 'http://feeds.transloc.com/segments.json?agencies=' + transloc_id_for_FIU

def get_fiu_bus_routes_from_transloc():
    bus_routes = None
    try:
        r = requests.get(transloc_routes_service_url, timeout=10)
        data = r.json()
        routes = data.get('routes') if data != None else None
        if routes != None:
            r = requests.get(transloc_route_segments_service_url, timeout=10)
            data = r.json()
            route_segments = data.get('routes') if data != None else None
            segment_segments = data.get('segments') if data != None else None
            if route_segments != None and segment_segments != None:
                r = requests.get(transloc_stops_service_url, timeout=10)
                data = r.json()
                route_stops = data.get('routes') if data != None else None
                if route_stops != None:
                    route_stops_for_route_ids = { str(item.get('id')) : item.get('stops') for item in route_stops }
                    cc = CompressCodec()
                    mm = MLS_merge()
                    fleet = 'fiu'
                    ndirections = 1
                    direction_names = ["Loop"]
                    bus_routes = []
                    tolerance = 1.5
                    route_segments_by_route_id = { item.get('id') : item.get('segments') for item in route_segments }
                    segments_by_segment_id = { 
                        item.get('id') : {
                            'points_positive' :
                                LS_simplify([(b, a) for (a, b) in cc.decodeLS(item.get('points'))], tolerance) 
                         } for item in segment_segments
                    }
                    for sbsi in segments_by_segment_id.values():
                        sbsi['points_negative'] = sbsi.get('points_positive')[::-1]
                    for d in routes:
                        route_id = d.get('id')
                        route_name = d.get('long_name')
                        color = d.get('color')
                        route_segment = route_segments_by_route_id.get(route_id)
                    
                        mls_points = []
                        for rs in route_segment:
                            rs_abs = abs(rs)
                            flip_direction = rs_abs != rs
                            points_name = 'points_negative' if flip_direction else 'points_positive'
                            points = segments_by_segment_id.get(rs_abs).get(points_name)
                            mls_points.append(points)
                        
                        mls_points = mm.merge(mls_points)
                        mls_points = [ cc.encodeLS(points, 6) for points in mls_points ]

                        compressed_multi_linestring = mls_points

                        stop_ids = route_stops_for_route_ids.get(str(route_id))

                        compressed_stop_ids = ','.join(str(item) for item in stop_ids)

                        direction_shapes = [mls_points]

                        if (route_id == None or route_name == None or color == None or ndirections == None or 
                            direction_names == None or direction_shapes == None or compressed_multi_linestring == None):
                            continue

                        record = [
                            fleet, route_id, route_name, color, compressed_multi_linestring, ndirections, direction_names, direction_shapes,
                            compressed_stop_ids
                        ]
                        bus_routes.append(record)
                else:
                    global_logger.error('get_fiu_bus_routes_from_transloc: transloc returned null stops')
            else:
                global_logger.error('get_fiu_bus_routes_from_transloc: transloc returned null route segments')
        else:
            global_logger.error('get_fiu_bus_routes_from_transloc: transloc returned null routes')
    except Exception as e:
        global_logger.error('get_fiu_bus_routes_from_transloc: ' + str(e))
        bus_routes = None

    return bus_routes

#BUS ETAS

utma_transit_server_bus_etas = utma_transit_server + "rtbusetas?agency="

def get_mdt_etas_from_transit_server():
    bus_etas = None
    had_exception = ''
    fleet = 'mdt'
    try:
        cur_bus_info = redis_load(mdt_last_bus_info_redis_key)
        if cur_bus_info != None:
            all_url = utma_transit_server_bus_etas + fleet.upper()
            r = requests.get(all_url, timeout=10)
            data = r.json()
            bus_etas = []
            est_day_only = get_eastern_current_day_only()
            for d in data:
                try:
                    bus_id = str(d.get('id'))
                    if cur_bus_info.get(bus_id):
                        route_id = str(d.get('route_id_in_feed'))
                        stop_ids = d.get('ETA_stop_ids_in_agency')
                        stop_etas = d.get('ETA_stop_hmss')
                        netas = len(stop_ids) if stop_ids != None else 0
                        if netas > 0:
                            netas = len(stop_ids)
                            if (bus_id == None or stop_ids == None or stop_etas == None or netas != len(stop_etas) or
                                route_id == None):
                                continue
                            for i in range(0, netas):
                                stop_id = stop_ids[i]
                                stop_eta = stop_etas[i]
                                est_stop_eta = est_day_only + datetime.timedelta(seconds=stop_eta)
                                record = [fleet, bus_id, stop_id, route_id, est_stop_eta]
                                bus_etas.append(record)
                except Exception as e:
                    if len(had_exception) == 0: had_exception = str(e)

    except Exception as e:
        global_logger.error('get_mdt_etas_from_transit_server fleet: ' + fleet + ': ' + str(e))
        bus_etas = None

    if len(had_exception) > 0: global_logger.error('get_mdt_etas_from_transit_server had exception in loop: ' + had_exception)

    #if bus_etas != None: global_logger.error('RETURNED BUS ETAS: ' + str(len(bus_etas)))
    #else: global_logger.error('RETURNED NONE BUS ETAS')

    return bus_etas

 #BUS FEEDS

mvideo_server = 'http://utma-video.cs.fiu.edu'

mvideo_server_bus_feeds = mvideo_server + "/api/hsls?format=json"

def get_bus_feeds_from_mvideo_server(): 
    return get_data_from_url(mvideo_server_bus_feeds, 'get_bus_feeds_from_mvideo_server', None, 10)

parking_server = 'http://xpect-itpa.cs.fiu.edu'
parking_server_headers = { "Authorization": "Token 1f691ebd8e5932dc6b925ed0c80430588b7d3fac", "Accept": "application/json" }

parking_server_parking_decals = parking_server + "/decals/"

def get_parking_decals_from_parking_server():
    data = get_data_from_url(parking_server_parking_decals, 'get_parking_decals_from_parking_server', parking_server_headers, 10)
    return data if data != None else []

parking_server_parking_recommendations = parking_server + "/sites/all_parking/"

def get_parking_recommendations_from_parking_server():
    data = get_data_from_url(parking_server_parking_recommendations,'get_parking_recommendations_from_parking_server', parking_server_headers, 10)
    return data if data != None else []

parking_server_parking_last_events = parking_server + "/sites/all_lastevents/"

def get_parking_last_events_from_parking_server():
    data = get_data_from_url(parking_server_parking_last_events, 'get_parking_last_events_from_parking_server', parking_server_headers, 10)
    return data if data != None else []

parking_server_parking_availability = parking_server + "/sites/availabilities/"

P_and_T_garage_count_url = 'https://patcount.fiu.edu/garagecount.xml'

P_and_T_GarageNameToParkingSiteIdMap = {
    'PG1': 35, 'PG2': 36, 'PG3': 37, 'PG4': 38, 'PG5': 39, 'PG6': 40,
    }

def get_spaces_and_max(from_map, prefix):
    spaces = max = None
    try:
        max = int(xml_get(from_map, prefix + 'Max'))
        if max != None:
            spaces = int(xml_get(from_map, prefix + 'Spaces'))
            if max < 0: max = 0
            if spaces < 0: spaces = 0
            if spaces > max: spaces = max
            spaces = max - spaces
    except Exception as e:
        spaces = max = None
        global_logger.error('get_spaces_and_max exception: ' + str(e));
    return spaces, max

def add_counts(site_id, result, rec, prefix):
    spaces, max = get_spaces_and_max(rec, prefix)
    if spaces != None and max != None:
        result.append({
            'site_id': site_id,
            'decalgroup': prefix,
            'total': max,
            'available': spaces,
            })

def get_parking_availability_from_P_and_T():
    xml_data = get_xml_data_from_url(P_and_T_garage_count_url, 'get_parking_availability_from_P_and_T', None, 10, True)
    result = []
    try:
        for rec in xml_data:
            site_id = P_and_T_GarageNameToParkingSiteIdMap.get(xml_get(rec, "GarageName"))
            if site_id != None:
                add_counts(site_id, result, rec, 'Student')
                add_counts(site_id, result, rec, 'Other')
    except Exception as e:
        result = []
        global_logger.error('get_parking_availability_from_P_and_T exception: ' + str(e));
    return result

def get_parking_availability_from_parking_server():
    data = get_data_from_url(parking_server_parking_availability, 'get_parking_availability_from_parking_server', parking_server_headers, 10)
    return data if data != None else []

streetsmart_server = 'http://streetsmartdemo.cloudapp.net'
streetsmart_lat = 25.75869
streetsmart_lng = -80.37388
streetsmart_road_graph_url = streetsmart_server + '/roadGraphProb?userLat=' + str(streetsmart_lat) + '&userLng=' + str(streetsmart_lng) + '&showRealTime=true'

def get_streetsmart_road_graph_from_streetsmart_server():
    return get_data_from_url(streetsmart_road_graph_url, 'get_streetsmart_road_graph_from_streetsmart_server', None, 10)

#ALL PURPOSE

def get_api_data(url):
    api_data = None
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            api_data = r.json()
        else:
            global_logger.error('get_api_data: request status code' + str(r.status_code))
    except Exception as e:
        api_data = None
        global_logger.error('get_api_data exception: ' + str(e))
    return api_data
