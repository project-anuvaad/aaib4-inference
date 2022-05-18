import time

from flask_restful import fields, marshal_with, reqparse, Resource
from flask import request, jsonify
from models import CustomResponse, Status
from config import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception, log_error
from config import poll_api_interval_sec
import uuid
import config
import json
from repository import RedisRepo, RedisFifoQueue

redisclient = RedisRepo()
fifo_redis_client = RedisFifoQueue(config.redis_fifo_queue_db) 

class NMTTranslateRedisReadResource(Resource):
    def post(self):
        api_input = request.get_json(force=True)
        return get_translation(api_input)


def get_translation(api_input):
    if len(api_input) > 0 and all(v in api_input for v in ['requestId']):
        request_id = api_input["requestId"]
        try:
            key = request_id
            response = redisclient.search_redis(key)
            if response:
                response = response[0]
                if 'translation_status' not in response.keys():
                    return {"status": "Translation in progress"}, 202
                else:
                    if response['translation_status'] == "Done":
                        del response['translation_status']
                        return response, 200
                    else:
                        statusCode = response["statusCode"]
                        del response['translation_status']
                        return response, statusCode
            else:
                return {"status": "Translation unavailable"}, 400
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in : {}".format(e), MODULE_CONTEXT, e)
            out = CustomResponse(status, request_id)
            return out.get_res_json_data(), 500
    else:
        log_info("ULCA API input missing mandatory data ('requestId')", MODULE_CONTEXT)
        status = Status.INVALID_API_REQUEST.value
        status['message'] = "Missing mandatory data ('requestId')"
        out = CustomResponse(status, api_input)
        return out.get_res_json_data(), 400


class NMTTranslateRedisWriteResource(Resource):
    def post(self):
        api_input = request.get_json(force=True)
        if config.use_redis_fifo_queue:
            return write_to_fifo_redis(api_input)
        else:
            return write_to_redis(api_input)


def write_to_redis(api_input):
    if len(api_input) > 0 and all(v in api_input for v in ['input', 'config']) and "modelId" in api_input.get(
            'config'):
        try:
            key = str(uuid.uuid4())
            api_input["requestId"] = key
            api_input["cronId"] = config.get_cron_id()
            status = redisclient.upsert_redis(key, api_input, True)
            if status:
                return {"requestId": key}, 202
            else:
                log_info("Write to redis FAILED!", MODULE_CONTEXT)
                out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                return out.get_res_json(), 500
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in : {}".format(e), MODULE_CONTEXT, e)
            out = CustomResponse(status, api_input)
            return out.get_res_json_data(), 500

def write_to_fifo_redis(api_input):
    if len(api_input) > 0 and all(v in api_input for v in ['input', 'config']) and "modelId" in api_input.get(
            'config'):
        try:
            key = str(uuid.uuid4())
            api_input["requestId"] = key
            api_input["cronId"] = config.get_cron_id()
            if api_input["config"]["language"]["sourceLanguage"] == 'en':
                fifo_db_key = 'en-indic'
            elif api_input["config"]["language"]["targetLanguage"] == 'en':
                fifo_db_key = 'indic-en'
            else:
                fifo_db_key = 'indic-indic'
            status = fifo_redis_client.rpush_redis(fifo_db_key, api_input)
            if status:
                status_return = {"requestId": key}, 202
                # return {"requestId": key}, 202
            else:
                log_info("Push to fifo redis FAILED!", MODULE_CONTEXT)
                out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                return out.get_res_json(), 500
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in : {}".format(e), MODULE_CONTEXT, e)
            out = CustomResponse(status, api_input)
            return out.get_res_json_data(), 500
        try:
            api_input["requestId"] = key
            api_input["cronId"] = config.get_cron_id()
            status = redisclient.upsert_redis(key, api_input, True)
            if status:
                return {"requestId": key}, 202
            else:
                log_info("Write to redis FAILED!", MODULE_CONTEXT)
                out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                return out.get_res_json(), 500
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in : {}".format(e), MODULE_CONTEXT, e)
            out = CustomResponse(status, api_input)
            return out.get_res_json_data(), 500

class TranslationDummy(Resource):
    def post(self):
        api_input = request.get_json(force=True)
        try:
            if config.use_redis_fifo_queue:
                response, code = write_to_fifo_redis(api_input)
            else:
                response, code = write_to_redis(api_input)
            if response:
                if 'requestId' in response.keys():
                    request_id = response["requestId"]
                    body = {"requestId": request_id}
                    final_response = None
                    while not final_response:
                        response, code = get_translation(body)
                        if response:
                            if "status" not in response.keys():
                                final_response = response
                        time.sleep(poll_api_interval_sec)
                    return final_response, 200
                else:
                    log_exception("No request ID in response", MODULE_CONTEXT, None)
                    out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                    return out.get_res_json_data(), 500
            else:
                log_exception("No response for search", MODULE_CONTEXT, None)
                out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                return out.get_res_json_data(), 500
        except Exception as e:
            log_exception("Something went wrong", MODULE_CONTEXT, e)
            out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
            return out.get_res_json_data(), 500
