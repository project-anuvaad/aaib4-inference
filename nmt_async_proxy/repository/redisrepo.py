import redis
from anuvaad_auditor.loghandler import log_info, log_exception
from config import MODULE_CONTEXT
import json
import config
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
                pipe.expire(i, record_expiry_in_sec)
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
                cron_id = config.get_cron_id()
                for val in db_values:
                    val = json.loads(val)
                    if 'cronId' in val.keys():
                        if val["cronId"] == cron_id:
                            if 'requestId' in val.keys():
                                values[val["requestId"]] = val
            return values
        except Exception as e:
            log_exception(f'Exception in redis get all keys: {e}', MODULE_CONTEXT, e)
            return None


class RedisFifoQueue:
    def __init__(self, db_number):
        self.db_number = db_number
        self.redis_client_connection = None

    def redis_instantiate(self):
        self.redis_client_connection = redis.Redis(host=redis_server_host, port=redis_server_port, db=self.db_number,
                                                   password=redis_server_pass)
        return self.redis_client_connection

    def get_redis_instance(self):
        if not self.redis_client_connection:
            return self.redis_instantiate()
        else:
            return self.redis_client_connection

    def rpush_redis(self, key, value):
        try:
            client = self.get_redis_instance()
            client.rpush(key, json.dumps(value))
            return True
        except Exception as e:
            log_exception(f'Exception in redis upsert: {e}', MODULE_CONTEXT, e)
            return None

    def get_max_queue_length_key(self, key_list):
        try:
            client = self.get_redis_instance()
            max_queue_name = max(key_list, key=lambda k: client.llen(k))
            return max_queue_name
        except Exception as e:
            log_exception(f'Exception in getting max queue length key: {e}', MODULE_CONTEXT, e)
            return None

    def get_queue_length(self, queue_key):
        try:
            client = self.get_redis_instance()
            length = client.llen(queue_key)
            return length
        except Exception as e:
            log_exception(f'Exception in getting queue legth: {e}', MODULE_CONTEXT, e)
            return None

    def get_batch(self, queue_key, batch_size):
        try:
            values = {}
            client = self.get_redis_instance()
            db_data = client.lpop(name=queue_key, count=batch_size)
            if db_data:
                for entry in db_data:
                    json_entry = json.loads(entry)
                    if "requestId" in json_entry.keys():
                        values[json_entry['requestId']] = json_entry
                return values
        except Exception as e:
            log_exception(f'Exception ocuured in popping the batch size from fifo queue: {e}', MODULE_CONTEXT, e)
            return None
