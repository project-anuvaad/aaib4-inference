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

## fetch model details
FETCH_MODEL_CONFG = os.path.join(APP_BASE_PATH, "config/fetch_models.json")

## truncation limit for sentence length
trunc_limit = 200

## max number of input sentences per batch (for inference service, specific to GPU type)
translation_batch_limit = os.environ.get('TRANSLATION_BATCH_LIMIT', 75)

## Time delay after which cron job will be executed
nmt_cron_interval_ms = os.environ.get('NMT_CRON_INTERVAL_MS', 500) 

if isinstance(nmt_cron_interval_ms, str):
    nmt_cron_interval_ms = eval(nmt_cron_interval_ms)

## supported languages
supported_languages = ['en','hi','ta','te','kn','pa','mr','as','or','ml','gu','bn']

## loaded model ('indic-en' OR 'en-indic' OR 'indic-indic')
model_to_load = os.environ.get('MODEL_NAME', '') # loads all three models 