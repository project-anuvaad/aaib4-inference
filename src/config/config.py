import os

redis_server_host = os.environ.get('REDIS_URL', 'localhost')
redis_server_port = os.environ.get('REDIS_PORT', 6380)
if isinstance(redis_server_port, str):
    redis_server_port = eval(redis_server_port)

redis_server_pass = os.environ.get('REDIS_PASS', None)

redis_db = os.environ.get('TRANSLATION_REDIS_DB', 0)
if isinstance(redis_db, str):
    redis_db = eval(redis_db)

record_expiry_in_sec = os.environ.get('TRANSLATION_REDIS_EXPIRY', 86400)
if isinstance(record_expiry_in_sec, str):
    record_expiry_in_sec = eval(record_expiry_in_sec)