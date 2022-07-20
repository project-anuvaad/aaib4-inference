from .kafka_topics import kafka_topic, bootstrap_server_boolean, bootstrap_server
import os

## app configuration variables
DEBUG = False
API_URL_PREFIX = ""
HOST = "0.0.0.0"
PORT = 5001

ENABLE_CORS = True

## application base path
APP_BASE_PATH = "src/"

## Module name
MODULE_NAME = "/aai4b-nmt-inference"
# MODULE_NAME_2 = "/nmt-inference"

## fetch model details
FETCH_MODEL_CONFG = os.path.join(APP_BASE_PATH, "config/fetch_models.json")

## truncation limit for sentence length
trunc_limit = 200

redis_server_host = os.environ.get('REDIS_URL', 'localhost')
redis_server_pass = os.environ.get('REDIS_PASS', 'mypassword')
redis_server_port = os.environ.get('REDIS_PORT', 6380)
if isinstance(redis_server_port, str):
    redis_server_port = eval(redis_server_port)

redis_db = os.environ.get('SENTENCE_TMX_REDIS_DB', 4)
if isinstance(redis_db, str):
    redis_db = eval(redis_db)

record_expiry_in_sec = os.environ.get('SENTENCE_TMX_REDIS_EXPIRY', 86400)
if isinstance(record_expiry_in_sec, str):
    record_expiry_in_sec = eval(record_expiry_in_sec)

model_attention_score_tmx_enabled = os.environ.get('MODEL_ATTENTION_SCORE_TMX_ENABLED', True) 
if isinstance(model_attention_score_tmx_enabled, str):
    if model_attention_score_tmx_enabled.casefold() == "TRUE".casefold():
        model_attention_score_tmx_enabled = True
    else:
        model_attention_score_tmx_enabled = False

# LABSE_PATH = os.path.join(APP_BASE_PATH, 'available_nmt_models/sbert.net_models_LaBSE')
LABSE_PATH = 'sentence-transformers/LaBSE'

## max number of input sentences per batch (for inference service, specific to GPU type)
translation_batch_limit = os.environ.get('TRANSLATION_BATCH_LIMIT', 75)

## supported languages
supported_languages = ['en','hi','ta','te','kn','pa','mr','as','or','ml','gu','bn']

## DB details
MONGO_SERVER_URL = os.environ.get('MONGO_CLUSTER_URL', 'localhost:27017')
DB_NAME = os.environ.get('MONGO_NMT_DB', 'anvaad-nmt-inference')
MONGO_NMT_MODELS_COLLECTION = os.environ.get('MONGO_NMT_MODELS_COLLECTION', 'anvaad-nmt-models')

## Supported languages (ISO-639-1 codes)
source = ['en','hi','mr','ta','te','kn','gu','pa','bn','ml','as','brx','doi','ks','kok','mai','mni','ne','or','sd','si','ur','sat','lus','njz','pnr','kha','grt','sa']