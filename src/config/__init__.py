from .kafka_topics import kafka_topic, bootstrap_server_boolean, bootstrap_server
import os

## app configuration variables
DEBUG = False
API_URL_PREFIX = ""
HOST = '0.0.0.0'
PORT = 5001

ENABLE_CORS = True

## application base path
APP_BASE_PATH = "src/"

## Module name
MODULE_NAME = "/aai4b-nmt-inference"
