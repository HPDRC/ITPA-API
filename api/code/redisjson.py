import redis
import json
import decimal
import os
import datetime
import sys
import logging
#import app

redisHost = os.environ.get('REDIS_HOST', "cache")
redisPort = int(os.environ.get('REDIS_PORT', "6379"))
redisDB = int(os.environ.get('REDIS_DB', "0"))
redisPass = os.environ.get('REDIS_PASSWORD', '')

redis_pool = redis.ConnectionPool(host=redisHost, port=redisPort, db=redisDB, password=redisPass)
#redis_conn = redis.StrictRedis(host=redisHost, port=redisPort, db=redisDB, password=redisPass)
redis_conn = redis.StrictRedis(connection_pool=redis_pool)

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
        if key != None and value != None: redis_conn.set(key, ejson_dumps(value))
    except Exception as e:
        logging.error('redis_set exception: ' + str(e));

def redis_load(key):
    result = None
    try:
        if key != None: data = redis_conn.get(key)
        if data != None: result = ejson_loads(data)
    except Exception as e:
        logging.error('redis_load exception: ' + str(e));
        result = None
    return result

def redis_expire(key, seconds_int):
    result = False
    try:
        if key != None: redis_conn.expire(key, seconds_int)
        result = True
    except Exception as e:
        logging.error('redis_expire exception: ' + str(e));
        result = False
    return result

def redis_hset(hash_key, field_key, value):
    result = False
    try:
        if hask_key != None and field_key != None and value != None: redis_conn.hset(hash_key, field_key, ejson_dumps(value))
        result = True
    except Exception as e:
        logging.error('redis_hset exception: ' + str(e));
        result = False
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
