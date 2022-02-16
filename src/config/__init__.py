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

## supported languages
supported_languages = ['en','hi','ta','te','kn','pa','mr','as','or','ml','gu','bn']

concurrent_processes = os.environ.get('NO_OF_PROCESSES', 2)