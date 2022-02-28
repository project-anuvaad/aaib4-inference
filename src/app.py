from audioop import mul
from subprocess import call
from flask import Flask, jsonify, request
from flask.blueprints import Blueprint
from flask_cors import CORS
from anuvaad_auditor.loghandler import log_info
import routes
import config
from cron_job import NMTcronjob, TranslationScheduler, NMTScheduleProcess
from utilities import MODULE_CONTEXT
import threading
from kafka_wrapper import KafkaTranslate
import multiprocessing

nmt_app = Flask(__name__)

def kafka_function():
    log_info('starting kafka from nmt-server on thread-1', MODULE_CONTEXT)
    KafkaTranslate.batch_translator([config.kafka_topic[0]['consumer']])


if config.bootstrap_server_boolean:
    t1 = threading.Thread(target=kafka_function)
    t1.start()

if config.ENABLE_CORS:
    cors = CORS(nmt_app, resources={r"/api/*": {"origins": "*"}})

for blueprint in vars(routes).values():
    if isinstance(blueprint, Blueprint):
        nmt_app.register_blueprint(blueprint, url_prefix=config.API_URL_PREFIX)

def call_nmt_translation_service():
    log_info(f"Starting the Translation service as a subprocess", MODULE_CONTEXT)
    NMTScheduleProcess()
    
if __name__ == "__main__":
    log_info('starting server at {} at port {}'.format(config.HOST, config.PORT), MODULE_CONTEXT)
    '''
    translation_scheduler = TranslationScheduler()
    translation_scheduler.schedule()
    '''

    '''
    wfm_jm_thread = NMTcronjob(threading.Event())
    wfm_jm_thread.start()
    '''
    p1 = multiprocessing.Process(target=call_nmt_translation_service, name='Translation Service')
    p1.start()
    nmt_app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)
    p1.join()