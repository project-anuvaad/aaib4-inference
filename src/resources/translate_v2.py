import json
from flask_restful import Resource
from flask import request
from html import escape
import functools

from anuvaad_auditor.loghandler import log_info, log_exception
from services import FairseqDocumentTranslateService, FairseqAutoCompleteTranslateService
from utilities import MODULE_CONTEXT
import config
from models import CustomResponse, Status

@functools.lru_cache(maxsize=None)
def get_v2_models():
    with open(config.FETCH_MODEL_CONFG) as f:
        confs = json.load(f)
    id2model = {
        model["model_id"]: model
        for model in confs["models"]
        if "version" in model and model["version"] >= 2
    }
    return id2model

@functools.lru_cache(maxsize=None, typed=True)
def get_model_id(source_language_code, target_language_code, is_constrained=False, version=2):
    if source_language_code == "en":
        direction = "en-indic"
    elif target_language_code == "en":
        direction = "indic-en"
    else:
        direction = "indic-indic"
    
    model_id = f"v{version}/{direction}"
    if is_constrained:
        model_id += "/constrained"
    return model_id

@functools.lru_cache(maxsize=None, typed=True)
def is_language_pair_supported(source_language_code, target_language_code, model_id):
    id2model = get_v2_models()
    if model_id not in id2model:
        return False
    
    model = id2model[model_id]
    supported_source_language_codes = model["source_language_codes"]
    supported_target_language_codes = model["target_language_codes"]

    return source_language_code in supported_source_language_codes and target_language_code in supported_target_language_codes

DEFAULT_CONTENT_TYPE = 'application/json'

class InteractiveMultiTranslateResource_v2(Resource):  
    def post(self):
        inputs = request.get_json(force=True)
        if len(inputs)>0:
            log_info("Making v2/interactive-translation API call",MODULE_CONTEXT)
            log_info("inputs---{}".format(inputs),MODULE_CONTEXT)

            for i in range(len(inputs)):
                inputs[i]["id"] = get_model_id(inputs[i]["source_language_code"], inputs[i]["target_language_code"])

            out = FairseqAutoCompleteTranslateService.constrained_translation(inputs)
            log_info("out from v2/interactive-translation done: {}".format(out.getresjson()), MODULE_CONTEXT)
            return out.jsonify_res()
        else:
            log_info("null inputs in request in v2/interactive-translation API", MODULE_CONTEXT)
            out = CustomResponse(Status.INVALID_API_REQUEST.value, None)
            return out.jsonify_res()        

class TranslateResourceM2M_v2(Resource):
    def post(self):
        '''
        End point when only src and tgt language information is available
        '''
        inputs = request.get_json(force=True)

        # Ensure that we have a received a proper JSON payload in the body
        if request.content_type != DEFAULT_CONTENT_TYPE:
            status = Status.INVALID_CONTENT_TYPE.value
            log_exception("v2 translate API | Invalid content type", MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 406, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
        
        # Check if all required input fields are present
        if not inputs or not all(v in inputs for v in ['src_list', 'source_language_code', 'target_language_code']):
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('src_list','source_language_code','target_language_code')"
            log_exception("v2 translate API | input missing mandatory data ('src_list','source_language_code','target_language_code')", MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 401, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}                    
        
        # Do not translate if input and output langs are same
        if inputs.get('source_language_code') == inputs.get('target_language_code'):
            status = Status.SAME_LANGUAGE_VALUE.value
            log_exception("v2 translate API | src and tgt code can't be same", MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 400, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
        
        model_id = get_model_id(inputs.get('source_language_code'), inputs.get('target_language_code'))
        if "indic-indic" in model_id:
            return self._get_pivoted_translation_response(inputs)
        else:
            return self._get_translation_response(inputs, model_id)
    
    def _get_translation_response(self, inputs, model_id):
        source_language_code, target_language_code = inputs.get('source_language_code'), inputs.get('target_language_code')

        # Check if the model supports the given lang-pair
        if not is_language_pair_supported(source_language_code, target_language_code, model_id):
            status = Status.UNSUPPORTED_LANGUAGE.value
            log_exception("v2 translate API | Unsupported input language code", MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 400, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
        
        try:  
            log_info("Making translate v2 API call", MODULE_CONTEXT)
            log_info("v2 translate API | input--- {}".format(inputs), MODULE_CONTEXT)
            input_src_list = inputs.get('src_list')
            
            translation_batch = {
                'id': model_id,
                'src_lang': source_language_code,
                'tgt_lang': target_language_code,
                'src_list': [item.get('src') for item in input_src_list],
            }
            output_batch = FairseqDocumentTranslateService.many_to_many_translator(translation_batch)

            # Stitch the translated sentences along with source sentences
            response_body = []
            for i, item in enumerate(input_src_list):
                item.update(
                    {'tgt': output_batch['tgt_list'][i]}
                )
                response_body.append(item)
            
            # Construct output payload
            out = CustomResponse(Status.SUCCESS.value, response_body) 
            log_info("Final output v2 API | {}".format(out.get_res_json()), MODULE_CONTEXT)     
            return out.get_res_json(), 200, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}   
        
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in v2 translate API resource child block: {}".format(e), MODULE_CONTEXT, e) 
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 500, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
    
    def _get_pivoted_translation_response(self, inputs, pivot_language_code="en"):
        source_language_code, target_language_code = inputs.get('source_language_code'), inputs.get('target_language_code')

        # First translate source to intermediate lang
        model_id = get_model_id(source_language_code, pivot_language_code)
        inputs["target_language_code"] = pivot_language_code
        response_json, status_code, http_headers = self._get_translation_response(inputs, model_id)
        if status_code != 200:
            # If error, just return it directly
            return response_json, status_code, http_headers

        # Now use intermediate translations as source
        intermediate_inputs = {
            "source_language_code": pivot_language_code,
            "target_language_code": target_language_code,
            "src_list": [{"src": item["tgt"]} for item in response_json["data"]],
        }
        model_id = get_model_id(pivot_language_code, target_language_code)
        response_json, status_code, http_headers = self._get_translation_response(intermediate_inputs, model_id)
        if status_code != 200:
            # If error, just return it directly
            return response_json, status_code, http_headers

        # Put original source sentences back and send the response
        for i, item in enumerate(inputs["src_list"]):
            response_json["data"][i]["src"] = item["src"]
        return response_json, status_code, http_headers

def html_encode(request_json_obj):
    try:
        request_json_obj["source_language_code"] = escape(request_json_obj["source_language_code"])
        request_json_obj["target_language_code"] = escape(request_json_obj["target_language_code"])
        for item in request_json_obj['src_list']:
            item['src'] = escape(item['src'])
    except Exception as e:
        log_exception("Exception caught in v2 translate API html encoding: {}".format(e),MODULE_CONTEXT,e)

    return request_json_obj
