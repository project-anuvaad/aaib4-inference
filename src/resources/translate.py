from flask_restful import fields, marshal_with, reqparse, Resource
from flask import request
from services import FairseqTranslateService, FairseqAutoCompleteTranslateService, FairseqDocumentTranslateService
from models import CustomResponse, Status
from utilities import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception
import datetime

        
class NMTTranslateResource(Resource):
    def post(self):
        '''
        ULCA end point
        '''
        translation_batch = {}
        src_list, output = list(), list()
        inputs = request.get_json(force=True)
        if len(inputs)>0 and all(v in inputs for v in ['input','config']) and "modelId" in inputs.get('config'):
            try:  
                log_info("Making API call for ULCA endpoint",MODULE_CONTEXT)
                log_info("inputs---{}".format(inputs),MODULE_CONTEXT)
                input_src_list = inputs.get('input')
                config = inputs.get('config')
                language = config.get('language')
                model_id = config.get('modelId')
                src_list = [i.get('source') for i in input_src_list]
                translation_batch = {'id':model_id,'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
                output_batch_dict_list = [{'target': output_batch['tgt_list'][i]}
                                                    for i in range(len(input_src_list))]
                for j,k in enumerate(input_src_list):
                    k.update(output_batch_dict_list[j])
                    output.append(k)
                final_output = {'config': config, 'output':output}     
                out = CustomResponse(Status.SUCCESS.value,final_output) 
                log_info("Final output from ULCA API: {}".format(out.get_res_json()),MODULE_CONTEXT)  
                return out.jsonify_data()     
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in  ULCA API child block: {}".format(e),MODULE_CONTEXT,e) 
                out = CustomResponse(status, inputs)
                return out.get_res_json_data(), 500
                
        else:
            log_info("ULCA API input missing mandatory data ('input','config,'modelId')",MODULE_CONTEXT)
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('input','config','modelId)"
            out = CustomResponse(status,inputs)
            return out.get_res_json_data(), 400            
        
class InteractiveMultiTranslateResourceNew(Resource):  
    def post(self):
        inputs = request.get_json(force=True)
        if len(inputs)>0:
            log_info("Making v0/interactive-translation API call",MODULE_CONTEXT)
            log_info("inputs---{}".format(inputs),MODULE_CONTEXT)
            out = FairseqAutoCompleteTranslateService.constrained_translation(inputs)
            log_info("out from v0/interactive-translation done: {}".format(out.getresjson()),MODULE_CONTEXT)
            return out.jsonify_res()
        else:
            log_info("null inputs in request in v0/interactive-translation API",MODULE_CONTEXT)
            out = CustomResponse(Status.INVALID_API_REQUEST.value,None)
            return out.jsonify_res()        

class TranslateResourceV1(Resource):
    def post(self):
        translation_batch = {}
        src_list, response_body = list(), list()
        inputs = request.get_json(force=True)
        if len(inputs)>0 and all(v in inputs for v in ['src_list','model_id']):
            try:  
                log_info("Making v1/translate API call",MODULE_CONTEXT)
                log_info("inputs---{}".format(inputs),MODULE_CONTEXT)
                input_src_list = inputs.get('src_list')
                src_list = [i.get('src') for i in input_src_list]
                translation_batch = {'id':inputs.get('model_id'),'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
                output_batch_dict_list = [{'tgt': output_batch['tgt_list'][i],
                                                    'tagged_tgt':output_batch['tagged_tgt_list'][i],'tagged_src':output_batch['tagged_src_list'][i]}
                                                    for i in range(len(input_src_list))]
                for j,k in enumerate(input_src_list):
                    k.update(output_batch_dict_list[j])
                    response_body.append(k)
                out = CustomResponse(Status.SUCCESS.value,response_body) 
                log_info("Final output from v1/translate API: {}".format(out.get_res_json()),MODULE_CONTEXT)        
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in batch_translator child block: {}".format(e),MODULE_CONTEXT,e) 
                out = CustomResponse(status, inputs)
            return out.jsonify_res()    
        else:
            log_info("API input missing mandatory data ('src_list','model_id')",MODULE_CONTEXT)
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('src_list','model_id')"
            out = CustomResponse(status,inputs)
            return out.jsonify_res()           
        
class TranslateResourcem2m(Resource):
    def post(self):
        translation_batch = {}
        src_list, response_body = list(), list()
        inputs = request.get_json(force=True)
        if len(inputs)>0 and all(v in inputs for v in ['src_list','source_language_code','target_language_code','model_id']):
            try:  
                log_info("Making m2m API call",MODULE_CONTEXT)
                log_info("inputs---{}".format(inputs),MODULE_CONTEXT)
                input_src_list = inputs.get('src_list')
                src_list = [i.get('src') for i in input_src_list]
                translation_batch = {'src_lang':inputs.get('source_language_code'),
                                     'tgt_lang':inputs.get('target_language_code'),'src_list': src_list}
                output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
                output_batch_dict_list = [{'tgt': output_batch['tgt_list'][i],
                                                    'tagged_tgt':output_batch['tagged_tgt_list'][i],'tagged_src':output_batch['tagged_src_list'][i]}
                                                    for i in range(len(input_src_list))]
                for j,k in enumerate(input_src_list):
                    k.update(output_batch_dict_list[j])
                    response_body.append(k)
                out = CustomResponse(Status.SUCCESS.value,response_body) 
                log_info("Final output from m2m API: {}".format(out.getresjson()),MODULE_CONTEXT)        
            except Exception as e:
                status = Status.SYSTEM_ERR.value
                status['message'] = str(e)
                log_exception("Exception caught in  m2m API child block: {}".format(e),MODULE_CONTEXT,e) 
                out = CustomResponse(status, inputs)
            return out.jsonify_res()    
        else:
            log_info("API input missing mandatory data ('src_list','model_id')",MODULE_CONTEXT)
            status = Status.INVALID_API_REQUEST.value
            status['message'] = "Missing mandatory data ('src_list','model_id')"
            out = CustomResponse(status,inputs)
            return out.jsonify_res()                   