import json
import time

import requests
from flask_restful import fields, marshal_with, reqparse, Resource
from flask import request
from services import FairseqTranslateService, FairseqAutoCompleteTranslateService, FairseqDocumentTranslateService
from models import CustomResponse, Status
from utilities import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception, log_error
from config import translation_batch_limit
from config import supported_languages
from html import escape
import uuid
import config
from repository import RedisRepo

redisclient = RedisRepo()


class NMTTranslateRedisReadResource(Resource):
    def post(self):
        api_input = request.get_json(force=True)
        if len(api_input) > 0 and all(v in api_input for v in ['requestId']):
            request_id = api_input["requestId"]
            try:
                key = request_id
                response = redisclient.search_redis(key)
                if response:
                    log_info("Value obtained for the key : {}".format(key), MODULE_CONTEXT)
                    response = response[0]
                    if 'translation_status' not in response.keys():
                        log_info("Translation is in progress", MODULE_CONTEXT)
                        out = CustomResponse(Status.SUCCESS.value, {"status": "Translation in progress"})
                        return out.get_res_json(), 200
                    else:
                        log_info("Translation fetched!", MODULE_CONTEXT)
                        del response['translation_status']
                        out = CustomResponse(Status.SUCCESS.value, response)
                        log_info("Final output of Redis Read | {}".format(out.get_res_json()), MODULE_CONTEXT)
                        return out.get_res_json(), 200
                else:
                    log_info("No records found of this key: {}".format(key), MODULE_CONTEXT)
                    out = CustomResponse(Status.INVALID_API_REQUEST.value, {"status": "Translation unavailable"})
                    return out.get_res_json(), 400
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
        if len(api_input) > 0 and all(v in api_input for v in ['input', 'config']) and "modelId" in api_input.get(
                'config'):
            try:
                log_info("Making call to redis write operation", MODULE_CONTEXT)
                log_info("input --- {}".format(api_input), MODULE_CONTEXT)
                key = str(uuid.uuid4())
                api_input["requestId"] = key
                status = redisclient.upsert_redis(key, api_input, True)
                if status:
                    out = CustomResponse(Status.SUCCESS.value, {"requestId": key})
                    log_info("Final output of Redis Write | {}".format(out.get_res_json()), MODULE_CONTEXT)
                    return out.get_res_json(), 202
                else:
                    log_info("Write to redis FAILED!", MODULE_CONTEXT)
                    out = CustomResponse(Status.SYSTEM_ERR.value, {"requestId": key})
                    return out.get_res_json(), 500
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in : {}".format(e), MODULE_CONTEXT, e)
                out = CustomResponse(status, api_input)
                return out.get_res_json_data(), 500


class NMTTranslateResource(Resource):
    def post(self):
        '''
        ULCA end point
        '''
        translation_batch = {}
        src_list, output = list(), list()
        inputs = request.get_json(force=True)
        if len(inputs) > 0 and all(v in inputs for v in ['input', 'config']) and "modelId" in inputs.get('config'):
            try:
                log_info("Making API call for ULCA endpoint", MODULE_CONTEXT)
                log_info("inputs---{}".format(inputs), MODULE_CONTEXT)
                input_src_list = inputs.get('input')
                config = inputs.get('config')
                language = config.get('language')
                model_id = config.get('modelId')
                src_list = [i.get('source') for i in input_src_list]
                if len(src_list) > translation_batch_limit:
                    raise Exception(
                        f"Number of sentences per request exceeded the limit of: {translation_batch_limit} sentences per batch")

                if model_id == 144:
                    translation_batch = {'id': model_id, 'src_lang': language['sourceLanguage'],
                                         'tgt_lang': language['targetLanguage'], 'src_list': src_list}
                    output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
                else:
                    translation_batch = {'id': model_id, 'src_list': src_list}
                    output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
                output_batch_dict_list = [{'target': output_batch['tgt_list'][i]}
                                          for i in range(len(input_src_list))]
                for j, k in enumerate(input_src_list):
                    k.update(output_batch_dict_list[j])
                    output.append(k)
                final_output = {'config': config, 'output': output}
                out = CustomResponse(Status.SUCCESS.value, final_output)
                log_info("Final output from ULCA API: {}".format(out.get_res_json()), MODULE_CONTEXT)
                return out.jsonify_data()
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in  ULCA API child block: {}".format(e), MODULE_CONTEXT, e)
                out = CustomResponse(status, inputs)
                return out.get_res_json_data(), 500

        else:
            log_info("ULCA API input missing mandatory data ('input','config,'modelId')", MODULE_CONTEXT)
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('input','config','modelId)"
            out = CustomResponse(status, inputs)
            return out.get_res_json_data(), 400


class InteractiveMultiTranslateResourceNew(Resource):
    def post(self):
        inputs = request.get_json(force=True)
        if len(inputs) > 0:
            log_info("Making v0/interactive-translation API call", MODULE_CONTEXT)
            log_info("inputs---{}".format(inputs), MODULE_CONTEXT)
            out = FairseqAutoCompleteTranslateService.constrained_translation(inputs)
            log_info("out from v0/interactive-translation done: {}".format(out.getresjson()), MODULE_CONTEXT)
            return out.jsonify_res()
        else:
            log_info("null inputs in request in v0/interactive-translation API", MODULE_CONTEXT)
            out = CustomResponse(Status.INVALID_API_REQUEST.value, None)
            return out.jsonify_res()


class TranslateResourceV1(Resource):
    def post(self):
        translation_batch = {}
        src_list, response_body = list(), list()
        inputs = request.get_json(force=True)
        if len(inputs) > 0 and all(v in inputs for v in ['src_list', 'model_id']):
            try:
                log_info("Making v1/translate API call", MODULE_CONTEXT)
                log_info("inputs---{}".format(inputs), MODULE_CONTEXT)
                input_src_list = inputs.get('src_list')
                src_list = [i.get('src') for i in input_src_list]
                if len(src_list) > translation_batch_limit:
                    raise Exception(
                        f"Number of sentences per request exceeded the limit of:{translation_batch_limit} sentences per batch")
                translation_batch = {'id': inputs.get('model_id'), 'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
                output_batch_dict_list = [{'tgt': output_batch['tgt_list'][i],
                                           'tagged_tgt': output_batch['tagged_tgt_list'][i],
                                           'tagged_src': output_batch['tagged_src_list'][i]}
                                          for i in range(len(input_src_list))]
                for j, k in enumerate(input_src_list):
                    k.update(output_batch_dict_list[j])
                    response_body.append(k)
                out = CustomResponse(Status.SUCCESS.value, response_body)
                log_info("Final output from v1/translate API: {}".format(out.get_res_json()), MODULE_CONTEXT)
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in batch_translator child block: {}".format(e), MODULE_CONTEXT, e)
                out = CustomResponse(status, inputs)
            return out.jsonify_res()
        else:
            log_info("API input missing mandatory data ('src_list','model_id')", MODULE_CONTEXT)
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('src_list','model_id')"
            out = CustomResponse(status, inputs)
            return out.jsonify_res()


class TranslateResourcem2m(Resource):
    def post(self):
        '''
        End point when only src and tgt language information is available
        '''
        translation_batch = {}
        src_list, response_body = list(), list()
        content_type = 'application/json'
        inputs = request.get_json(force=True)
        if request.content_type != content_type:
            status = Status.INVALID_CONTENT_TYPE.value
            log_exception("v1.1 translate API | Invalid content type", MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 406, {'Content-Type': content_type, 'X-Content-Type-Options': 'nosniff'}

        if len(inputs) > 0 and all(v in inputs for v in ['src_list', 'source_language_code', 'target_language_code']):
            if (inputs.get('source_language_code') not in supported_languages) or (
                    inputs.get('target_language_code') not in supported_languages):
                status = Status.UNSUPPORTED_LANGUAGE.value
                log_exception("v1.1 translate API | Unsupported input language code", MODULE_CONTEXT, status['message'])
                out = CustomResponse(status, html_encode(inputs))
                return out.get_res_json(), 400, {'Content-Type': content_type, 'X-Content-Type-Options': 'nosniff'}
            elif inputs.get('source_language_code') == inputs.get('target_language_code'):
                status = Status.SAME_LANGUAGE_VALUE.value
                log_exception("v1.1 translate API | src and tgt code can't be same", MODULE_CONTEXT, status['message'])
                out = CustomResponse(status, html_encode(inputs))
                return out.get_res_json(), 400, {'Content-Type': content_type, 'X-Content-Type-Options': 'nosniff'}

            try:
                log_info("Making translate v1.1 API call", MODULE_CONTEXT)
                log_info("v1.1 translate API | input--- {}".format(inputs), MODULE_CONTEXT)
                input_src_list = inputs.get('src_list')
                src_list = [i.get('src') for i in input_src_list]
                m_id = get_model_id(inputs.get('source_language_code'), inputs.get('target_language_code'))
                translation_batch = {'id': m_id, 'src_lang': inputs.get('source_language_code'),
                                     'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
                output_batch_dict_list = [{'tgt': output_batch['tgt_list'][i]}
                                          for i in range(len(input_src_list))]
                for j, k in enumerate(input_src_list):
                    k.update(output_batch_dict_list[j])
                    response_body.append(k)
                out = CustomResponse(Status.SUCCESS.value, response_body)
                log_info("Final output v1.1 API | {}".format(out.get_res_json()), MODULE_CONTEXT)
                return out.get_res_json(), 200, {'Content-Type': content_type, 'X-Content-Type-Options': 'nosniff'}
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in v1.1 translate API resource child block: {}".format(e),
                              MODULE_CONTEXT, e)
                out = CustomResponse(status, html_encode(inputs))
                return out.get_res_json(), 500, {'Content-Type': content_type, 'X-Content-Type-Options': 'nosniff'}
        else:
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('src_list','source_language_code','target_language_code')"
            log_exception(
                "v1.1 translate API | input missing mandatory data ('src_list','source_language_code','target_language_code')",
                MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 401, {'Content-Type': content_type, 'X-Content-Type-Options': 'nosniff'}


class NMTTranslateResource_async():
    def __init__(self):
        pass

    def async_call(self, inputs):
        model_id, src_lang, tgt_lang, src_list = inputs
        try:
            if model_id == 144:
                translation_batch = {'id': model_id, 'src_lang': src_lang,
                                     'tgt_lang': tgt_lang, 'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
            else:
                translation_batch = {'id': model_id, 'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
            final_output = {"tgt_list": output_batch['tgt_list']}
            return final_output
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in  ULCA async-call for batch translation child block: {}".format(e),
                          MODULE_CONTEXT, e)
            return {"error": status}


class TranslationDummy(Resource):
    def post(self):
        api_input = request.get_json(force=True)
        try:
            write_endpoint = f'http://localhost:5001/aai4b-nmt-inference/v0/{config.model_to_load}/translate/async'
            log_info("Calling translate/sync....", MODULE_CONTEXT)
            response = call_api(write_endpoint, api_input, "userId")
            log_info("sync response received!", MODULE_CONTEXT)
            if response:
                log_info(f'WRITE RESPONSE: {response}', MODULE_CONTEXT)
                request_id = response['data']["requestId"]
                read_endpoint = f'http://localhost:5001/aai4b-nmt-inference/v0/{config.model_to_load}/search-translation'
                body = {"requestId": request_id}
                final_response = None
                count = 0
                while not final_response:
                    response = call_api(read_endpoint, body, "userId")
                    if response:
                        if "status" not in response["data"].keys():
                            log_info(f'FINAL READ RESPONSE: {response}', MODULE_CONTEXT)
                            final_response = response
                    count += 1
                    time.sleep(0.5)
                log_info(f"No of polls at rate of 1req per 500ms done to get translation: {count}", MODULE_CONTEXT)
                out = CustomResponse(Status.SUCCESS.value, final_response)
                return out.get_res_json(), 200
            else:
                log_exception("Something went wrong", MODULE_CONTEXT, None)
                out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                return out.get_res_json_data(), 500
        except Exception as e:
            log_exception("Something went wrong", MODULE_CONTEXT, e)
            out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
            return out.get_res_json_data(), 500


def get_model_id(source_language_code, target_language_code):
    if source_language_code and source_language_code == 'en':
        m_id = 103
    elif target_language_code and target_language_code == 'en':
        m_id = 100
    else:
        m_id = 144

    return m_id


def html_encode(request_json_obj):
    try:
        request_json_obj["source_language_code"] = escape(request_json_obj["source_language_code"])
        request_json_obj["target_language_code"] = escape(request_json_obj["target_language_code"])
        for item in request_json_obj['src_list']:
            item['src'] = escape(item['src'])
    except Exception as e:
        log_exception("Exception caught in v1.1 translate API html encoding: {}".format(e), MODULE_CONTEXT, e)

    return request_json_obj


# Initialises and fetches redis client

def ulca_translate_kernel(model_id, language, src_list):
    if model_id == 144:
        translation_batch = {'id': model_id, 'src_lang': language['sourceLanguage'],
                             'tgt_lang': language['targetLanguage'], 'src_list': src_list}
        output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
    else:
        translation_batch = {'id': model_id, 'src_list': src_list}
        output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)

    return output_batch


def call_api(uri, api_input, user_id):
    try:
        log_info("URI: " + uri, None)
        api_headers = {'userid': user_id, 'x-user-id': user_id,
                       'Content-Type': 'application/json'}
        response = requests.post(
            url=uri, json=api_input, headers=api_headers)
        if response is not None:
            if response.text is not None:
                log_info(response.text, None)
                data = json.loads(response.text)
                return data
            else:
                log_error("API response was None !", api_input, None)
                return None
        else:
            log_error("API call failed!", api_input, None)
            return None
    except Exception as e:
        log_exception(
            "Exception while making the api call: " + str(e), api_input, e)
        return None
