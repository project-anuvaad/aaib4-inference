import redis
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
import json

from config import redis_server_host, redis_server_port, redis_server_pass, redis_db, record_expiry_in_sec

redis_client_datasets = None


class RedisRepo:
    def __init__(self):
        pass

    def redis_instantiate(self):
        global redis_client_datasets
        redis_client_datasets = redis.Redis(host=redis_server_host, port=redis_server_port, db=redis_db,
                                            password=redis_server_pass)
        return redis_client_datasets

    def get_redis_instance(self):
        global redis_client_datasets
        if not redis_client_datasets:
            return self.redis_instantiate()
        else:
            return redis_client_datasets

    def bulk_upsert_redis(self, ip_dict):
        try:
            client = self.get_redis_instance()
            pipe = client.pipeline()
            for i in ip_dict.keys():
                pipe.set(i, json.dumps(ip_dict[i]))
            pipe.execute()
            return True
        except Exception as e:
            log_exception(f'Exception in bulk redis upsert: {e}', MODULE_CONTEXT, e)
            return None

    def upsert_redis(self, key, value, expiry):
        try:
            client = self.get_redis_instance()
            if expiry:
                client.set(key, json.dumps(value), ex=record_expiry_in_sec)
            else:
                client.set(key, json.dumps(value))
            return True
        except Exception as e:
            log_exception(f'Exception in redis upsert: {e}', MODULE_CONTEXT, e)
            return None

    def search_redis(self, key):
        try:
            client = self.get_redis_instance()
            result = []
            val = client.get(key)
            if val:
                result.append(json.loads(val))
            return result
        except Exception as e:
            log_exception(f'Exception in redis search: {e}', MODULE_CONTEXT, e)
            return None

    def get_all_keys(self):
        try:
            client = self.get_redis_instance()
            return client.keys()
        except Exception as e:
            log_exception(f'Exception in redis get all keys: {e}', MODULE_CONTEXT, e)
            return None

    def get_list_of_values(self, keys):
        try:
            values = {}
            client = self.get_redis_instance()
            db_values = client.mget(keys)
            if db_values:
                for val in db_values:
                    val = json.loads(val)
                    if 'requestId' in val.keys():
                        values[val["requestId"]] = val
            return values
        except Exception as e:
            log_exception(f'Exception in redis get all keys: {e}', MODULE_CONTEXT, e)
            return None
