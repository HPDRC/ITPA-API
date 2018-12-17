import redis
import json
import decimal
import os
import datetime
import sys

from celery.utils.log import get_task_logger

import utils

logging = get_task_logger(__name__)

redisHost = os.environ.get('REDIS_HOST', "cache")
redisPort = int(os.environ.get('REDIS_PORT', "6379"))
redisDB = int(os.environ.get('REDIS_DB', "0"))
redisFlowerDB = int(os.environ.get('redisFlowerDB', "0"))
redisPass = os.environ.get('REDIS_PASSWORD', '')

redis_pool = redis.ConnectionPool(host=redisHost, port=redisPort, db=redisDB, password=redisPass)
#redis_conn = redis.StrictRedis(host=redisHost, port=redisPort, db=redisDB, password=redisPass)
redis_conn = redis.StrictRedis(connection_pool=redis_pool)

def get_celery_redis():
    return 'redis://:' + redisPass + '@' + redisHost + ':' + str(redisPort) + '/' + str(redisFlowerDB)

def redis_publish(channel, message):
    try: redis_conn.publish(channel, message)
    except Exception as e: logging.error('redis_publish exception: ' + str(e));

def get_redis_pubsub():
    try: return redis_conn.pubsub()
    except: return None

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            ARGS = ('year', 'month', 'day', 'hour', 'minute',
                     'second', 'microsecond')
            return {'__type__': 'datetime.datetime',
                    'args': [getattr(obj, a) for a in ARGS]}
        elif isinstance(obj, datetime.date):
            ARGS = ('year', 'month', 'day')
            return {'__type__': 'datetime.date',
                    'args': [getattr(obj, a) for a in ARGS]}
        elif isinstance(obj, datetime.time):
            ARGS = ('hour', 'minute', 'second', 'microsecond')
            return {'__type__': 'datetime.time',
                    'args': [getattr(obj, a) for a in ARGS]}
        elif isinstance(obj, datetime.timedelta):
            ARGS = ('days', 'seconds', 'microseconds')
            return {'__type__': 'datetime.timedelta',
                    'args': [getattr(obj, a) for a in ARGS]}
        elif isinstance(obj, decimal.Decimal):
            return {'__type__': 'decimal.Decimal',
                    'args': [str(obj),]}
        else:
            return super().default(obj)

class EnhancedJSONDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, object_hook=self.object_hook,
                         **kwargs)

    def object_hook(self, d): 
        if '__type__' not in d:
            return d
        o = sys.modules[__name__]
        for e in d['__type__'].split('.'):
            o = getattr(o, e)
        args, kwargs = d.get('args', ()), d.get('kwargs', {})
        return o(*args, **kwargs)

def ejson_dumps(value): return json.dumps(value, cls=EnhancedJSONEncoder)
def ejson_loads(value): return json.loads(value, cls=EnhancedJSONDecoder)

def redis_set(key, value):
    try:
        if value != None: redis_conn.set(key, ejson_dumps(value))
    except Exception as e:
        logging.error('redis_set exception: ' + str(e));

def redis_load(key):
    result = None
    try:
        data = redis_conn.get(key)
        if data != None: result = ejson_loads(data)
    except Exception as e:
        logging.error('redis_load exception: ' + str(e));
        result = None
    return result

def redis_expire(key, seconds_int):
    result = False
    try:
        if key != None:
            redis_conn.expire(key, seconds_int)
            result = True
    except Exception as e:
        logging.error('redis_expire exception: ' + str(e));
        result = False
    return result

def redis_hset(hash_key, field_key, value):
    result = False
    try:
        if hash_key != None and field_key != None and value != None:
            redis_conn.hset(hash_key, field_key, ejson_dumps(value))
            result = True
    except Exception as e:
        logging.error('redis_hset exception: ' + str(e));
        result = False
    return result

def redis_hget(hash_key, field_key):
    result = None
    try:
        if hash_key != None and field_key != None: 
            result = redis_conn.hget(hash_key, field_key)
            if result != None:
                result = ejson_loads(result)
    except Exception as e:
        logging.error('redis_hget exception: ' + str(e));
        result = None
    return result

def redis_hload_all(hash_key):
    result = None
    try:
        if hash_key != None:
            data = redis_conn.hgetall(hash_key)
            if data != None:
                result = []
                for value in data.values():
                    result.append(ejson_loads(value))
    except Exception as e:
        logging.error('redis_hload_all exception: ' + str(e));
        result = None
    return result

def get_point_features_from_array(the_array, name_field_lon = 'lon', name_field_lat = 'lat'):
    return ([
        {
            "geometry": {
                "type": "point",
                "coordinates": [r.get(name_field_lon), r.get(name_field_lat)]
            },
            "properties": r,
            "type": "Feature"
        } for r in the_array
    ]) 

def get_shape_features_from_array(the_array, name_field_shape = 'polygon'):
    return ([
        {
            "geometry": {
                "type": name_field_shape,
                "coordinates": r.get(name_field_shape)
            },
            "properties": { key: val for (key, val) in r.items() if key != name_field_shape },
            "type": "Feature"
        } for r in the_array
    ]) 

def get_polygon_features_from_array(the_array): return get_shape_features_from_array(the_array, 'polygon')

def get_feature_collection_from_array(utc_time_stamp, the_array, features_getter = get_point_features_from_array): 
    features = features_getter(the_array)
    features_count = len(features) if features != None else -1
    return { 'features': features, 'type':'FeatureCollection', 'FeatureCount': features_count,
        'timestamp': utc_time_stamp,
    }

features_suffix = '?features'

def redis_set_records(redis_base_key, current_records, features_getter = get_point_features_from_array):
    try:
        count = len(current_records) if current_records != None else 0
        if count == 0: current_records = []
        utc_time_stamp = utils.get_date_isoformat(datetime.datetime.utcnow())
        non_feature_result = {
            'data': current_records,
            'count': count,
            'timestamp': utc_time_stamp
        }
        redis_set(redis_base_key, non_feature_result)
        if features_getter != None:
            feature_result = get_feature_collection_from_array(utc_time_stamp, current_records, features_getter)
            redis_set(redis_base_key + features_suffix, feature_result)
    except Exception as e:
        logging.error('redis_set_records: ' + str(e));
