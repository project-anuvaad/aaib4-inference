from flask_restful import fields, marshal_with, reqparse, Resource
from flask import request
from services import FairseqTranslateService, FairseqAutoCompleteTranslateService
from models import CustomResponse, Status
from utilities import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception
import datetime

        
class NMTTranslateResource(Resource):
    def post(self):
        inputs = request.get_json(force=True)
        if len(inputs)>0:
            log_info("Making v3/translate-anuvaad API call",MODULE_CONTEXT)
            log_info("inputs---{}".format(inputs),MODULE_CONTEXT)
            out = FairseqTranslateService.simple_translation(inputs)
            log_info("Final output from v3/translate-anuvaad API: {}".format(out.getresjson()),MODULE_CONTEXT)
            return out.getres()
        else:
            log_info("null inputs in request in translate-anuvaad API",MODULE_CONTEXT)
            out = CustomResponse(Status.INVALID_API_REQUEST.value,None)
            return out.getres()             
        
class InteractiveMultiTranslateResourceNew(Resource):  
    def post(self):
        inputs = request.get_json(force=True)
        if len(inputs)>0:
            log_info("Making v2/interactive-translation API call",MODULE_CONTEXT)
            log_info("inputs---{}".format(inputs),MODULE_CONTEXT)
            # log_info(entry_exit_log(LOG_TAGS["input"],inputs))
            out = FairseqAutoCompleteTranslateService.constrained_translation(inputs)
            log_info("out from v2/interactive-translation done: {}".format(out.getresjson()),MODULE_CONTEXT)
            # log_info(entry_exit_log(LOG_TAGS["output"],out))
            return out.getres()
        else:
            log_info("null inputs in request in v2/interactive-translation API",MODULE_CONTEXT)
            out = CustomResponse(Status.INVALID_API_REQUEST.value,None)
            return out.getres()        