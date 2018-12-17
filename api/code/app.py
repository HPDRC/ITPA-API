# code/app.py

import logging
import sys
import os
import json
import datetime

from flask import Flask
from flask import jsonify
from flask import request, make_response, current_app
from functools import update_wrapper

from redisjson import (redis_load, redis_hload_all)

from utils import (get_user_rights, can_admin_itpa, is_itpa_user, do_add_change_parking_site, 
    get_congestion_details,
    do_add_change_notification, start_task_async,do_get_buses_history, do_get_device_tracking_history,
    do_track_device, get_date_isoformat,
    add_new_bus_video_to_db,
    end_record_bus_video_to_db,
    get_bus_videos_from_db,
    do_del_bus_video,
    do_del_bus_video_frames,
    )

ITPA_ADMIN_TOKEN = os.environ.get('ITPA_ADMIN_TOKEN', 'sdlfksldfjlsdfjow')

from flask_cors import CORS

application = Flask(__name__)
CORS(application)

application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '2b025fd4-3df4-4884-946b-799cc1d793cc')

env_video_token = os.environ.get('VIDEO_TOKEN', 'sdflsfkjsf;lsf;jou0u0u0ujj98h394h39hr')
env_recorder_token = os.environ.get('VIDEO_RECORDER_TOKEN', 'sdflsfkjsf;lsf;jou0u0u0ujj98h394h39hr')

features_suffix = '?features'

def reply_to_request(base_redis_key):
    redis_key = base_redis_key
    if request.args.get('features') != None: redis_key += features_suffix
    result = redis_load(redis_key)
    if result == None: result = { "OK": False }
    return jsonify(result)

@application.route('/')
def application_root():
    result = {"data":"hello, world."}
    return jsonify(**result)

@application.route('/fl511_congestion_details', methods=['GET'])
def fl511_congestion_details():
    return jsonify(**get_congestion_details(request.args))
    """
    result = {}
    congestion_id = request.args.get('congestion_id')
    if congestion_id != None:
        #result['img'] = '<img src="/map/Cctv/662--2"/>'
        result = getfl511_congestion_details(congestion_id)
    return jsonify(**result)
    """

@application.route('/fl511_congestions', methods=['GET'])
def fl511_congestions(): return reply_to_request('fl511_congestions')

@application.route('/fl511_cameras', methods=['GET'])
def fl511_cameras(): return reply_to_request('fl511_cameras')

@application.route('/fl511_message_boards_current', methods=['GET'])
def fl511_message_boards(): return reply_to_request('fl511_message_boards_current')

@application.route('/fl511_messages_current', methods=['GET'])
def fl511_messages_current(): return reply_to_request('fl511_messages_current')

@application.route('/itpa_buses_current', methods=['GET'])
def itpa_buses_current(): return reply_to_request('itpa_buses_current')

@application.route('/flhsmv_incidents_current', methods=['GET'])
def flhsmv_incidents_current(): return reply_to_request('flhsmv_incidents_current')

@application.route('/itpa_parking_sites', methods=['GET'])
def itpa_parking_sites(): return reply_to_request('itpa_parking_sites')

@application.route('/itpa_parking_sites_all', methods=['GET'])
def itpa_parking_sites_all(): return reply_to_request('itpa_parking_sites_all')

@application.route('/itpa_bus_stops', methods=['GET'])
def itpa_bus_stops(): return reply_to_request('itpa_bus_stops')

@application.route('/itpa_bus_routes', methods=['GET'])
def itpa_bus_routes(): return reply_to_request('itpa_bus_routes')

@application.route('/itpa_bus_etas', methods=['GET'])
def itpa_bus_etas(): return reply_to_request('itpa_bus_etas')

@application.route('/itpa_parking_decals', methods=['GET'])
def itpa_parking_decals(): return reply_to_request('itpa_parking_decals')

@application.route('/itpa_parking_recommendations', methods=['GET'])
def itpa_parking_recommendations(): return reply_to_request('itpa_parking_recommendations')

@application.route('/itpa_parking_last_events', methods=['GET'])
def itpa_parking_last_events(): return reply_to_request('itpa_parking_last_events')

@application.route('/itpa_parking_availability', methods=['GET'])
def itpa_parking_availability(): return reply_to_request('itpa_parking_availability')

@application.route('/itpa_bus_feeds', methods=['GET'])
def itpa_bus_feeds(): return reply_to_request('itpa_bus_feeds')

@application.route('/itpa_notifications_active', methods=['GET'])
def itpa_notifications_active(): return reply_to_request('itpa_notifications_active')

@application.route('/itpa_notifications_all', methods=['GET'])
def itpa_notifications_all(): return reply_to_request('itpa_notifications_all')

@application.route('/streetsmart_road_graph', methods=['GET'])
def streetsmart_road_graph(): return reply_to_request('streetsmart_road_graph')

@application.route('/itpa_current_device_tracking', methods=['GET'])
def itpa_current_device_tracking(): 
    status = False
    result = None
    token = request.args.get('token')
    ok = token == ITPA_ADMIN_TOKEN
    if not ok:
        user_rights = get_user_rights(token)
        ok = can_admin_itpa(user_rights)
    if ok:
        result = reply_to_request('itpa_current_device_tracking')
    else:
        result = jsonify({ 'status': False })
    return result

@application.route('/itpa_buses_history', methods=['GET'])
def itpa_buses_history(): 
    status = False
    result = None
    token = request.args.get('token')
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        result = do_get_buses_history(request.args)
    else:
        result = { 'status': False }
    return jsonify(result)

@application.route('/itpa_device_tracking_history', methods=['GET'])
def itpa_device_tracking_history(): 
    status = False
    result = None
    token = request.args.get('token')
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        result = do_get_device_tracking_history(request.args)
    else:
        result = { 'status': False }
    return jsonify(result)

@application.route('/itpa_track_device', methods=['GET'])
def itpa_track_device(): 
    status = False
    result = None
    token = request.args.get('token')
    user_rights = get_user_rights(token)
    if is_itpa_user(user_rights):
        result = do_track_device(request.args)
    else:
        result = { 'status': False }
    return jsonify(result)

@application.route('/itpa_notifications_add_change', methods=['POST'])
def itpa_notifications_add_change(): 
    result = False
    added_id = None
    token = request.args.get('token')
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        result, added_id = do_add_change_notification(request.get_json(silent=True))
    return jsonify({ 'status': result, 'id': added_id });

@application.route('/itpa_parking_sites_add_change', methods=['POST'])
def itpa_parking_sites_add_change():
    result = False
    added_id = None
    token = request.args.get('token')
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        result, added_id = do_add_change_parking_site(request.get_json(silent=True))
    return jsonify({ 'status': result, 'id': added_id });

@application.route('/current_stats', methods=['GET'])
def current_stats(): return reply_to_request('current_stats')

@application.route('/exec_task', methods=['GET'])
def exec_task():
    result = { 'ok': False, 'msg': 'sorry' };
    token = request.args.get('token')
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        task_name = request.args.get('name')
        result = start_task_async(task_name) if task_name != None else 'task name missing'
    return jsonify({ 'result': result })

"""

addNewApiVideo: {"bus_fleet":"utma","bus_id":"5011","bus_name":"MPV-3","camera_type":"FakeCam","uuid":"71f6ac99-83c3-41fa-a12c-997560d1e3db","createdOn":1534785124460}
endRecordNewApiVideo: {"bus_fleet":"utma","bus_id":"5011","bus_name":"MPV-3","camera_type":"FakeCam","uuid":"71f6ac99-83c3-41fa-a12c-997560d1e3db","createdOn":1534785124460,"recordingEnded":1534785136307}

"""

@application.route('/add_new_bus_video', methods=['GET'])
def add_new_bus_video():
    token = request.args.get('token')
    status = 401
    if token == ITPA_ADMIN_TOKEN:
        status = add_new_bus_video_to_db(request.args)
    resp = jsonify({'ok': status == 200})
    resp.status_code = status
    return resp

@application.route('/end_record_bus_video', methods=['GET'])
def end_record_bus_video():
    token = request.args.get('token')
    status = 401
    if token == ITPA_ADMIN_TOKEN:
        status = end_record_bus_video_to_db(request.args)
    resp = jsonify({'ok': status == 200})
    resp.status_code = status
    return resp

@application.route('/itpa_bus_videos', methods=['GET'])
def itpa_bus_videos(): 
    return jsonify(get_bus_videos_from_db())

@application.route('/del_bus_video', methods=['POST'])
def del_bus_video(): 
    status = 401
    request_json = request.get_json(silent=True)
    token = request_json.get('token') if request_json != None else None
    #application.logger.error('got token ' + str(token));
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        status = do_del_bus_video(request_json)
    resp = jsonify({'ok': status == 200})
    resp.status_code = status
    return resp

@application.route('/del_bus_video_frames', methods=['POST'])
def del_bus_video_frames(): 
    status = 401
    request_json = request.get_json(silent=True)
    token = request_json.get('token') if request_json != None else None
    #application.logger.error('got token ' + str(token));
    user_rights = get_user_rights(token)
    if can_admin_itpa(user_rights):
        status = do_del_bus_video_frames(request_json)
    resp = jsonify({'ok': status == 200})
    resp.status_code = status
    return resp

if __name__ == '__main__':
    application.logger.setLevel(logging.INFO)
    application.logger.info('app initialized in main');
    application.run(debug=True,host='0.0.0.0')
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)
    application.logger.info('app initialized not in main');
