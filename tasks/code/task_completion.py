import requests
import os
import datetime

from redisjson import (redis_load, redis_set, ejson_loads, ejson_dumps, redis_hset, redis_hget, get_redis_pubsub, 
    redis_publish,
    redis_set_records,
    redis_hload_all,
    )

import utils

import web_connect

from celery.utils.log import get_task_logger

logging = get_task_logger(__name__)

SOCKETIO_SERVER = os.environ.get('SOCKETIO_SERVER', 'socketio')
SOCKETIO_PORT = os.environ.get('SOCKETIO_PORT', '1337')
SOCKETIO_TOKEN = os.environ.get('SOCKETIO_TOKEN', '')
socket_io_url = 'http://' + SOCKETIO_SERVER + ':' + SOCKETIO_PORT + '/'
socket_io_notify_data_change_url = socket_io_url + 'notify_data_change'
socket_io_current_stats_url = socket_io_url + 'current_stats'

ITPA_SERVER = os.environ.get('ITPA_SERVER', 'itpa')
ITPA_PORT = os.environ.get('ITPA_PORT', '8060')
ITPA_ADMIN_TOKEN = os.environ.get('ITPA_ADMIN_TOKEN', '8060')
itpa_server = 'http://' +  ITPA_SERVER + ':' + ITPA_PORT + '/'

API_SERVER = os.environ.get('API_SERVER', 'api')
API_PORT = os.environ.get('API_PORT', '8000')

api_url = 'http://' + API_SERVER + ':' + API_PORT + '/'
api_features_suffix = '?features'

api_itpa_buses_current = 'itpa_buses_current'
api_itpa_buses_current_features = api_itpa_buses_current + api_features_suffix

api_itpa_parking_sites = 'itpa_parking_sites'
api_itpa_parking_sites_features = api_itpa_parking_sites + api_features_suffix

api_itpa_parking_sites_all = 'itpa_parking_sites_all'
api_itpa_parking_sites_all_features = api_itpa_parking_sites_all + api_features_suffix

api_fl511_congestions = 'fl511_congestions'
api_fl511_congestions_features = api_fl511_congestions + api_features_suffix

api_fl511_cameras = 'fl511_cameras'
api_fl511_cameras_features = api_fl511_cameras + api_features_suffix

api_fl511_messages_current = 'fl511_messages_current'
api_fl511_messages_current_features = api_fl511_messages_current + api_features_suffix

api_flhsmv_incidents_current = 'flhsmv_incidents_current'
api_flhsmv_incidents_current_features = api_flhsmv_incidents_current + api_features_suffix

api_itpa_bus_etas = 'itpa_bus_etas'

api_itpa_bus_routes = 'itpa_bus_routes'

api_itpa_bus_stops = 'itpa_bus_stops'
api_itpa_bus_stops_features = api_itpa_bus_stops + api_features_suffix

api_itpa_bus_feeds = 'itpa_bus_feeds'

api_current_stats = 'current_stats'

api_itpa_parking_recommendations = 'itpa_parking_recommendations'

api_itpa_parking_decals = 'itpa_parking_decals'

api_itpa_parking_last_events = 'itpa_parking_last_events'

api_itpa_parking_availability = 'itpa_parking_availability'

api_itpa_notifications_active = 'itpa_notifications_active'
api_itpa_notifications_all = 'itpa_notifications_all'

api_streetsmart_road_graph = 'streetsmart_road_graph'

api_itpa_current_device_tracking = 'itpa_current_device_tracking'
api_itpa_current_device_tracking_features = api_itpa_current_device_tracking + api_features_suffix

itpa_user_list = 'user_list'
itpa_get_itpa_user_list = itpa_server + itpa_user_list + '?token=' + ITPA_ADMIN_TOKEN

data_set_change_redis_channel_name = 'data_set_change'

#redis_pubsub = get_redis_pubsub();
#redis_pubsub.subscribe(data_set_change_redis_channel_name)

current_stats_log_redis_key = api_current_stats + '_hset'

def update_current_stats_from_db():
    redis_set_records(api_current_stats, redis_hload_all(current_stats_log_redis_key), None)

def log_task(task_name):
    try:
        log_entry_name = 'itpa_log_' + task_name
        log_record = {
            'task_name': task_name,
            'is_data_gathering': True,
            'completed_on': utils.get_date_isoformat(datetime.datetime.utcnow()),
            'count': 1,
        }
        old_record = redis_hget(current_stats_log_redis_key, log_entry_name)
        if old_record != None:
            old_count = old_record.get('count')
            log_record['count'] = old_count + 1 if old_count != None else 1
        redis_hset(current_stats_log_redis_key, log_entry_name, log_record)
    except Exception as e:
        logging.error('log_task exception: ' + str(e))

def get_socketio_stats_from_socketio_server(): return web_connect.get_api_data(socket_io_current_stats_url)

def update_socketio_stats_on_db(records):
    try:
        for record in records:
            redis_hset(current_stats_log_redis_key, record.get('task_name'), record)
    except Exception as e:
        logging.error('update_socketio_stats_on_db exception: ' + str(e))

def update_current_user_list_from_db():
    redis_set_records(itpa_user_list, web_connect.get_api_data(itpa_get_itpa_user_list))

task_spec_by_task_name = {
    'tasks.update_itpa_parking_sites': {
        'redis_keys': [ api_itpa_parking_sites, api_itpa_parking_sites_features, api_itpa_parking_sites_all, api_itpa_parking_sites_all_features, ],
    },
    'tasks.update_itpa_buses': {
        'redis_keys': [ api_itpa_buses_current, api_itpa_buses_current_features, ],
        'log': True,
    },

    'tasks.update_fl511_cameras': {
        'redis_keys': [ api_fl511_cameras, api_fl511_cameras_features, ],
        'log': True,
    },

    'tasks.update_fl511_congestions': {
        'redis_keys': [ api_fl511_congestions, api_fl511_congestions_features, ],
        'log': True,
    },

    'tasks.update_fl511_message_boards_messages': {
        'redis_keys': [ api_fl511_messages_current, api_fl511_messages_current_features, ],
        'log': True,
    },
    'tasks.update_flhsmv_incidents': {
        'redis_keys': [ api_flhsmv_incidents_current, api_flhsmv_incidents_current_features, ],
        'log': True,
    },
    'tasks.update_itpa_bus_etas': {
        'redis_keys': [ api_itpa_bus_etas, ],
        'log': True,
    },
    'tasks.update_itpa_bus_routes': {
        'redis_keys': [ api_itpa_bus_routes, ],
    },
    'tasks.update_itpa_bus_stops': {
        'redis_keys': [ api_itpa_bus_stops, api_itpa_bus_stops_features ],
    },
    'tasks.update_itpa_bus_feeds': {
        'redis_keys': [ api_itpa_bus_feeds ],
    },
    'tasks.update_itpa_parking_decals': {
        'redis_keys': [ api_itpa_parking_decals ],
    },
    'tasks.update_itpa_parking_recommendations': {
        'redis_keys': [ api_itpa_parking_recommendations, ],
        'log': True,
    },
    'tasks.update_itpa_parking_last_events': {
        'redis_keys': [ api_itpa_parking_last_events, ],
        'log': True,
    },
    'tasks.update_itpa_parking_availability': {
        'redis_keys': [ api_itpa_parking_availability, ],
        'log': True,
    },
    'tasks.update_itpa_notifications': {
        'redis_keys': [ api_itpa_notifications_active, api_itpa_notifications_all ]
    },
    'tasks.update_streetsmart_road_graph': {
        'redis_keys': [ api_streetsmart_road_graph, ],
        'log': True,
    },
    'tasks.update_itpa_user_list': {
        'redis_keys': [ itpa_user_list ]
    },
    'tasks.update_itpa_current_device_tracking': {
        'redis_keys': [ api_itpa_current_device_tracking, api_itpa_current_device_tracking_features ]
    },
    'tasks.update_current_stats': {
        'redis_keys': [ api_current_stats ]
    },
}

def notify_task_completion(task_name):
    try:
        task_spec = task_spec_by_task_name.get(task_name)
        if task_spec != None:
            task_redis_keys = task_spec.get('redis_keys')
            for redis_key in task_redis_keys:
                redis_publish(data_set_change_redis_channel_name, redis_key);
            if task_spec.get('log') == True: log_task(task_name)
    except Exception as e:
        logging.error('notify_task_completion exception: ' + str(e))
