import os
import sys
import time
import logging
import requests
import re
import datetime
import mysql.connector
from mysql.connector import ClientFlag

from celery import Celery, Task
from celery.utils.log import get_task_logger

import redisjson

from web_connect import (load_fl511_message_boards_from_fl511, load_fl511_messages_from_fl511, load_flhsmv_incidents_from_flhsmv,
    load_fl511_congestions_from_fl511,
    load_fl511_cameras_from_fl511,
    load_mdt_buses_from_mdt, load_fiu_buses_from_transloc, load_utma_buses_from_transit_server,
    get_mdt_bus_stops_from_transit_server, get_utma_bus_stops_from_transit_server,
    get_mdt_bus_routes_from_transit_server, get_utma_bus_routes_from_transit_server,
    get_fiu_bus_routes_from_transloc, get_fiu_bus_stops_from_transloc,
    get_mdt_etas_from_transit_server,
    get_bus_feeds_from_mvideo_server,
    get_parking_decals_from_parking_server,
    get_parking_availability_from_P_and_T,
    get_parking_recommendations_from_parking_server,
    get_parking_last_events_from_parking_server,
    get_parking_availability_from_parking_server,
    get_streetsmart_road_graph_from_streetsmart_server,
    )

from db_connect import (update_fl511_message_boards_on_db, update_fl511_messages_on_db, update_flhsmv_incidents_on_db,
    update_fl511_messages_from_db, update_flhsmv_incidents_from_db, update_buses_on_db, update_buses_from_db, update_parking_sites_from_db,
    update_fl511_congestions_on_db,
    update_fl511_cameras_on_db,
    update_itpa_bus_stops_on_db, update_itpa_bus_stops_from_db, update_itpa_bus_routes_on_db, update_itpa_bus_routes_from_db,
    update_itpa_bus_etas_from_db, update_itpa_bus_etas_on_db,
    update_bus_feeds_on_db,
    update_parking_decals_on_db,
    update_parking_recommendations_on_db,
    update_parking_last_events_on_db,
    update_parking_availability_on_db,
    update_parking_server_availabilities_on_db,
    update_itpa_notifications_from_db,
    update_streetsmart_road_graph_on_db,
    update_current_device_tracking_from_db,
    )

from task_completion import (notify_task_completion, get_socketio_stats_from_socketio_server, 
    update_socketio_stats_on_db,
    update_current_stats_from_db,
    update_current_user_list_from_db,
    )

global_logger = get_task_logger(__name__)

celeryRedis = redisjson.get_celery_redis()
app = Celery('tasks', broker=celeryRedis, backend=celeryRedis)

app.conf.result_expires = 3600

app.worker_redirect_stdouts = False
app.conf.timezone = 'UTC'
app.enable_utc = True;

def process_request_data(current_data, data_updater):
    data_count = -1
    try:
        data_count = len(current_data) if current_data != None else -1
        if data_count >= 0: data_updater(current_data)
    except Exception as e:
        data_count = -1
        global_logger.error('process_request_data exception: ' + str(e))
    return data_count

def process_request(data_loader, data_updater, suffix):
    data_count = -1
    try: data_count = process_request_data(data_loader(), data_updater)
    except Exception as e:
        data_count = -1
        global_logger.error('process_request exception: ' + str(e))
    return str(data_count) + ' ' + suffix

def do_update_fl511_congestions(): return process_request(load_fl511_congestions_from_fl511, update_fl511_congestions_on_db, 'congestions')

def do_update_fl511_cameras(): return process_request(load_fl511_cameras_from_fl511, update_fl511_cameras_on_db, 'cameras')

def do_update_fl511_message_boards(): return process_request(load_fl511_message_boards_from_fl511, update_fl511_message_boards_on_db, 'message boards')
def do_update_fl511_message_boards_messages(): return process_request(load_fl511_messages_from_fl511, update_fl511_messages_on_db, 'messages')
def do_update_flhsmv_incidents(): return process_request(load_flhsmv_incidents_from_flhsmv, update_flhsmv_incidents_on_db, 'incidents')

def do_update_mdt_bus_stops(): return process_request(get_mdt_bus_stops_from_transit_server, update_itpa_bus_stops_on_db, 'mdt bus stops')
def do_update_mdt_bus_routes(): return process_request(get_mdt_bus_routes_from_transit_server, update_itpa_bus_routes_on_db, 'mdt bus routes')

def do_update_fiu_bus_stops(): return process_request(get_fiu_bus_stops_from_transloc, update_itpa_bus_stops_on_db, 'fiu bus stops')
def do_update_fiu_bus_routes(): return process_request(get_fiu_bus_routes_from_transloc, update_itpa_bus_routes_on_db, 'fiu bus routes')

def do_update_utma_bus_stops(): return process_request(get_utma_bus_stops_from_transit_server, update_itpa_bus_stops_on_db, 'utma bus stops')
def do_update_utma_bus_routes(): return process_request(get_utma_bus_routes_from_transit_server, update_itpa_bus_routes_on_db, 'utma bus routes')

def do_update_mdt_bus_etas_from_transit_server(): return process_request(get_mdt_etas_from_transit_server, update_itpa_bus_etas_on_db, 'mdt etas from transit server')

def do_update_itpa_user_list():
    update_current_user_list_from_db()
    return 'updating itpa user list'

def do_update_itpa_current_device_tracking():
    update_current_device_tracking_from_db()
    return 'updated device tracking'

def do_update_itpa_buses():
    update_buses_from_db()
    return 'updated buses'

def do_update_itpa_bus_stops():
    update_itpa_bus_stops_from_db()
    return 'updated stops'

def do_update_itpa_bus_routes():
    update_itpa_bus_routes_from_db()
    return 'updated routes'

def do_update_itpa_bus_etas():
    update_itpa_bus_etas_from_db()
    return 'updated bus etas';

def do_update_itpa_notifications():
    update_itpa_notifications_from_db()
    return 'updated itpa notifications';

def process_update_bus_positions(loader, loader_has_etas = False):
    current_buses = archive_buses = bus_etas = None
    if loader_has_etas:
        current_buses, archive_buses, bus_etas = loader()
    else:
        current_buses, archive_buses = loader()
    nc = len(current_buses) if current_buses != None else -1
    na = len(archive_buses) if archive_buses != None else -1 

    update_buses_on_db(current_buses, archive_buses)
    str_return = 'current: ' + str(nc) + ' archived: ' + str(na)

    if loader_has_etas:
        ne = process_request_data(bus_etas, update_itpa_bus_etas_on_db)
        str_return += ' etas: ' + str(ne)

    #global_logger.info('process_update_bus_positions: ' + str_returl)

    return str_return

def do_update_mdt_bus_positions(): return process_update_bus_positions(load_mdt_buses_from_mdt)
def do_update_utma_bus_positions(): return process_update_bus_positions(load_utma_buses_from_transit_server)

def do_update_fiu_bus_positions(): return process_update_bus_positions(load_fiu_buses_from_transloc, True)

def do_update_itpa_bus_feeds(): 
    return process_request(get_bus_feeds_from_mvideo_server, update_bus_feeds_on_db, 'itpa bus feeds from mvideo server')

def do_update_itpa_parking_decals(): 
    return process_request(get_parking_decals_from_parking_server, update_parking_decals_on_db, 'itpa parking decals from parking server')

def do_update_itpa_parking_recommendations(): 
    return process_request(get_parking_recommendations_from_parking_server, update_parking_recommendations_on_db, 'itpa parking recommendations from parking server')

def do_update_itpa_parking_last_events(): 
    return process_request(get_parking_last_events_from_parking_server, update_parking_last_events_on_db, 'itpa parking last events from parking server')

def do_update_itpa_parking_availability(): 
    return process_request(get_parking_availability_from_P_and_T, update_parking_availability_on_db, 'itpa parking availability from P&T')

def do_update_itpa_parking_availability2(): 
    return process_request(get_parking_availability_from_parking_server, update_parking_server_availabilities_on_db, 'itpa parking availability from parking server')

def do_update_streetsmart_road_graph():
    return process_request(get_streetsmart_road_graph_from_streetsmart_server, update_streetsmart_road_graph_on_db, 'streetsmart road graph from streetsmart server')

def do_update_socketio_stats():
    return process_request(get_socketio_stats_from_socketio_server, update_socketio_stats_on_db, 'socketio stats from socketio server')

def do_update_current_stats():
    update_current_stats_from_db()
    return 'updated current stats'

def do_update_itpa_parking_sites():
    update_parking_sites_from_db()
    return 'updated parking sites'

class NotifierTask(Task):
    """Task that sends notification on completion."""
    abstract = True
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        notify_task_completion(self.name)

@app.task(name='tasks.update_fl511_congestions', base=NotifierTask)
def update_fl511_congestions(): return do_update_fl511_congestions()

@app.task(name='tasks.update_fl511_cameras', base=NotifierTask)
def update_fl511_cameras(): return do_update_fl511_cameras()

@app.task(name='tasks.update_fl511_message_boards')
def update_fl511_message_boards(): return do_update_fl511_message_boards();

@app.task(name='tasks.update_fl511_message_boards_messages', base=NotifierTask)
def update_fl511_message_boards_messages(): return do_update_fl511_message_boards_messages()

@app.task(name='tasks.update_flhsmv_incidents', base=NotifierTask)
def update_flhsmv_incidents(): return do_update_flhsmv_incidents()

@app.task(name='tasks.update_itpa_bus_feeds', base=NotifierTask)
def update_itpa_bus_feeds(): return do_update_itpa_bus_feeds()

@app.task(name='tasks.update_itpa_parking_sites', base=NotifierTask)
def update_itpa_parking_sites(): return do_update_itpa_parking_sites()

@app.task(name='tasks.update_itpa_parking_decals', base=NotifierTask)
def update_itpa_parking_decals(): return do_update_itpa_parking_decals()

@app.task(name='tasks.update_itpa_parking_recommendations', base=NotifierTask)
def update_itpa_parking_recommendations(): return do_update_itpa_parking_recommendations()

@app.task(name='tasks.update_itpa_parking_last_events', base=NotifierTask)
def update_itpa_parking_last_events(): return do_update_itpa_parking_last_events()

@app.task(name='tasks.update_itpa_parking_availability', base=NotifierTask)
def update_itpa_parking_availability(): return do_update_itpa_parking_availability()

@app.task(name='tasks.update_itpa_parking_availability2', base=NotifierTask)
def update_itpa_parking_availability2(): return do_update_itpa_parking_availability2()

@app.task(name='tasks.update_mdt_bus_positions')
def update_mdt_bus_positions(): return do_update_mdt_bus_positions()

@app.task(name='tasks.update_fiu_bus_positions')
def update_fiu_bus_positions(): return do_update_fiu_bus_positions()

@app.task(name='tasks.update_utma_bus_positions')
def update_utma_bus_positions(): return do_update_utma_bus_positions()

@app.task(name='tasks.update_itpa_buses', base=NotifierTask)
def update_itpa_buses(): return do_update_itpa_buses()

@app.task(name='tasks.update_mdt_bus_stops')
def update_mdt_bus_stops(): return do_update_mdt_bus_stops()

@app.task(name='tasks.update_fiu_bus_stops')
def update_fiu_bus_stops(): return do_update_fiu_bus_stops()

@app.task(name='tasks.update_utma_bus_stops')
def update_utma_bus_stops(): return do_update_utma_bus_stops()

@app.task(name='tasks.update_itpa_bus_stops', base=NotifierTask)
def update_itpa_bus_stops(): return do_update_itpa_bus_stops()

@app.task(name='tasks.update_mdt_bus_routes')
def update_mdt_bus_routes(): return do_update_mdt_bus_routes()

@app.task(name='tasks.update_fiu_bus_routes')
def update_fiu_bus_routes(): return do_update_fiu_bus_routes()

@app.task(name='tasks.update_utma_bus_routes')
def update_utma_bus_routes(): return do_update_utma_bus_routes()

@app.task(name='tasks.update_itpa_bus_routes', base=NotifierTask)
def update_itpa_bus_routes(): return do_update_itpa_bus_routes()

@app.task(name='tasks.update_itpa_bus_etas', base=NotifierTask)
def update_itpa_bus_etas(): return do_update_itpa_bus_etas()

@app.task(name='tasks.update_mdt_bus_etas_from_transit_server')
def update_mdt_bus_etas_from_transit_server(): return do_update_mdt_bus_etas_from_transit_server()

@app.task(name='tasks.update_itpa_notifications', base=NotifierTask)
def update_itpa_notifications(): return do_update_itpa_notifications()

@app.task(name='tasks.update_streetsmart_road_graph', base=NotifierTask)
def update_streetsmart_road_graph(): return do_update_streetsmart_road_graph()

@app.task(name='tasks.update_itpa_user_list', base=NotifierTask)
def update_itpa_user_list(): return do_update_itpa_user_list()

@app.task(name='tasks.update_current_stats', base=NotifierTask)
def update_current_stats(): return do_update_current_stats()

@app.task(name='tasks.update_socketio_stats', base=NotifierTask)
def update_socketio_stats(): return do_update_socketio_stats()

@app.task(name='tasks.update_itpa_current_device_tracking', base=NotifierTask)
def update_itpa_current_device_tracking(): return do_update_itpa_current_device_tracking()

def do_post_init_updates():
    #global_logger.error('post_init_updates')
    #do_update_itpa_bus_stops()
    #do_update_itpa_bus_routes()
    #update_fl511_messages_from_db()
    #update_flhsmv_incidents_from_db()

    update_itpa_parking_sites.apply_async(countdown=1);
    update_itpa_parking_decals.apply_async(countdown=3);

    update_fl511_message_boards.apply_async(countdown=2);
    update_fl511_message_boards_messages.apply_async(countdown=10);

    update_fl511_congestions.apply_async(countdown=4);
    update_fl511_cameras.apply_async(countdown=4);

    update_itpa_bus_stops.apply_async(countdown=5);
    update_itpa_bus_routes.apply_async(countdown=5);

@app.task(name='tasks.post_init_updates')
def post_init_updates(): return do_post_init_updates()

bus_routes_itpa_update_minutes = 15
bus_routes_import_update_minutes = 30

bus_stops_itpa_update_minutes = 15
bus_stops_import_update_minutes = 30

fl511_congestions_update_seconds = 60 * 10
fl511_cameras_update_minutes = 60

fl511_message_boards_update_minutes = 10
fl511_message_board_messages_update_minutes = 1

flhsmv_incidents_update_minutes = 1

itpa_parking_sites_update_minutes = 30
itpa_parking_decals_update_minutes = 30

itpa_parking_from_parking_server_updates_seconds = 20

itpa_parking_recommendations_update_seconds = itpa_parking_from_parking_server_updates_seconds
itpa_parking_last_events_update_seconds = itpa_parking_from_parking_server_updates_seconds
itpa_parking_availability_update_seconds = itpa_parking_from_parking_server_updates_seconds
itpa_parking_availability2_update_seconds = itpa_parking_from_parking_server_updates_seconds

itpa_buses_update_secs = 2
mdt_buses_update_secs = 5
fiu_buses_update_secs = 1
utma_buses_update_secs = 1

itpa_bus_etas_update_seconds = 10
import_bus_etas_from_transit_server_update_seconds = 5

itpa_bus_feeds_update_seconds = 5

streetsmart_road_graph_update_seconds = 10

update_itpa_user_list_seconds = 10

update_itpa_current_device_tracking_seconds = 10

update_current_stats_seconds = 10

update_socketio_stats_seconds = 5

delay_buses = True
delay_buses = False

if delay_buses:
    big_value = 10000
    itpa_buses_update_secs = big_value
    mdt_buses_update_secs = big_value
    fiu_buses_update_secs = big_value
    utma_buses_update_secs = big_value
    itpa_bus_etas_update_seconds = big_value
    import_bus_etas_from_transit_server_update_seconds = big_value
    itpa_bus_feeds_update_seconds = big_value

app.conf.beat_schedule = {
    'update_fl511_congestions': {
        'task': update_fl511_congestions.name,
        'schedule': datetime.timedelta(seconds=fl511_congestions_update_seconds)
    },
    'update_fl511_cameras': {
        'task': update_fl511_cameras.name,
        'schedule': datetime.timedelta(minutes=fl511_cameras_update_minutes)
    },
    'update_fl511_message_boards': {
        'task': update_fl511_message_boards.name,
        'schedule': datetime.timedelta(minutes=fl511_message_boards_update_minutes)
    },
    'update_fl511_message_board_messages': {
        'task': update_fl511_message_boards_messages.name,
        'schedule': datetime.timedelta(minutes=fl511_message_board_messages_update_minutes)
    },
    'update_flhsmv_incidents': {
        'task': update_flhsmv_incidents.name,
        'schedule': datetime.timedelta(minutes=flhsmv_incidents_update_minutes)
    },
    'update_itpa_bus_feeds': {
        'task': update_itpa_bus_feeds.name,
        'schedule': datetime.timedelta(seconds=itpa_bus_feeds_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_parking_sites': {
        'task': update_itpa_parking_sites.name,
        'schedule': datetime.timedelta(minutes=itpa_parking_sites_update_minutes)
    },
    'update_itpa_parking_recommendations': {
        'task': update_itpa_parking_recommendations.name,
        'schedule': datetime.timedelta(seconds=itpa_parking_recommendations_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_parking_decals': {
        'task': update_itpa_parking_decals.name,
        'schedule': datetime.timedelta(minutes=itpa_parking_decals_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_parking_last_events': {
        'task': update_itpa_parking_last_events.name,
        'schedule': datetime.timedelta(seconds=itpa_parking_last_events_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_parking_availability': {
        'task': update_itpa_parking_availability.name,
        'schedule': datetime.timedelta(seconds=itpa_parking_availability_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_parking_availability2': {
        'task': update_itpa_parking_availability2.name,
        'schedule': datetime.timedelta(seconds=itpa_parking_availability2_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_streetsmart_road_graph': {
        'task': update_streetsmart_road_graph.name,
        'schedule': datetime.timedelta(seconds=streetsmart_road_graph_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_buses': {
        'task': update_itpa_buses.name,
        'schedule': datetime.timedelta(seconds=itpa_buses_update_secs)
    },
    'update_mdt_bus_positions': {
        'task': update_mdt_bus_positions.name,
        'schedule': datetime.timedelta(seconds=mdt_buses_update_secs)
    },
    'update_fiu_bus_positions': {
        'task': update_fiu_bus_positions.name,
        'schedule': datetime.timedelta(seconds=fiu_buses_update_secs)
    },
    'update_utma_bus_positions': {
        'task': update_utma_bus_positions.name,
        'schedule': datetime.timedelta(seconds=utma_buses_update_secs)
    },
    'update_itpa_bus_stops': {
        'task': update_itpa_bus_stops.name,
        'schedule': datetime.timedelta(minutes=bus_stops_itpa_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_mdt_bus_stops': {
        'task': update_mdt_bus_stops.name,
        'schedule': datetime.timedelta(minutes=bus_stops_import_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_fiu_bus_stops': {
        'task': update_fiu_bus_stops.name,
        'schedule': datetime.timedelta(minutes=bus_stops_import_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_utma_bus_stops': {
        'task': update_utma_bus_stops.name,
        'schedule': datetime.timedelta(minutes=bus_stops_import_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_bus_routes': {
        'task': update_itpa_bus_routes.name,
        'schedule': datetime.timedelta(minutes=bus_routes_itpa_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_mdt_bus_routes': {
        'task': update_mdt_bus_routes.name,
        'schedule': datetime.timedelta(minutes=bus_routes_import_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_fiu_bus_routes': {
        'task': update_fiu_bus_routes.name,
        'schedule': datetime.timedelta(minutes=bus_routes_import_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_utma_bus_routes': {
        'task': update_utma_bus_routes.name,
        'schedule': datetime.timedelta(minutes=bus_routes_import_update_minutes)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_bus_etas': {
        'task': update_itpa_bus_etas.name,
        'schedule': datetime.timedelta(seconds=itpa_bus_etas_update_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_mdt_bus_etas_from_transit_server': {
        'task': update_mdt_bus_etas_from_transit_server.name,
        #'schedule': datetime.timedelta(seconds=import_bus_etas_from_transit_server_update_seconds)
        'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_user_list': {
        'task': update_itpa_user_list.name,
        'schedule': datetime.timedelta(seconds=update_itpa_user_list_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_itpa_current_device_tracking': {
        'task': update_itpa_current_device_tracking.name,
        'schedule': datetime.timedelta(seconds=update_itpa_current_device_tracking_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_current_stats': {
        'task': update_current_stats.name,
        'schedule': datetime.timedelta(seconds=update_current_stats_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
    'update_socketio_stats': {
        'task': update_socketio_stats.name,
        'schedule': datetime.timedelta(seconds=update_socketio_stats_seconds)
        #'schedule': datetime.timedelta(seconds=5)
    },
}

FLOWER_SERVER = os.environ.get('FLOWER_SERVER', "flower")
FLOWER_PORT = os.environ.get('FLOWER_PORT', "5555")
FLOWER_USER = os.environ.get('CELERY_USER', "itpa")
FLOWER_PASSWORD = os.environ.get('CELERY_PASSWORD', "itpa")

from celery.signals import worker_ready
@worker_ready.connect
def on_worker_ready(**_):
    global_logger.info('on worker ready')
    do_update_fl511_congestions()
    do_update_fl511_cameras()
    do_update_fl511_message_boards()
    do_update_fl511_message_boards_messages()
    do_update_itpa_bus_feeds()
    do_update_itpa_parking_decals()
    do_update_itpa_parking_recommendations()
    do_update_itpa_parking_last_events()
    do_update_itpa_parking_availability()
    do_update_itpa_parking_availability2()
    do_update_itpa_parking_sites()
    do_update_itpa_notifications()
    do_update_streetsmart_road_graph()
    do_update_itpa_user_list()
    do_update_socketio_stats()
    do_update_current_stats()
    do_update_itpa_current_device_tracking()
    do_update_itpa_buses()
    do_update_mdt_bus_stops()
    do_update_mdt_bus_routes()
    do_update_fiu_bus_stops()
    do_update_fiu_bus_routes()
    do_update_utma_bus_stops()
    do_update_utma_bus_routes()
    do_update_itpa_bus_etas()

    post_init_updates.apply_async(countdown=10)

if __name__ == '__main__':
    global_logger.info('started from main')
    print('started from main')
else:
    global_logger.info('started NOT from main')
    print('started NOT from main')
