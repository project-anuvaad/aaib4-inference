from kafka_wrapper.producer import get_producer
from kafka_wrapper.consumer import get_consumer
from models import CustomResponse, Status
import config
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
import sys
import datetime
from services import FairseqDocumentTranslateService

import functools

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

class KafkaTranslate_v2:

                
    @staticmethod
    def batch_translator(c_topic):
        ''' New method for batch translation '''      
        log_info('KafkaTranslate: batch_translator',MODULE_CONTEXT)  
        out = {}
        msg_count,msg_sent = 0,0
        consumer = get_consumer(c_topic)
        producer = get_producer()
        try:
            for msg in consumer:
                producer_topic = [topic["producer"] for topic in config.kafka_topic if topic["consumer"] == msg.topic][0]
                log_info("Producer for current consumer:{} is-{}".format(msg.topic,producer_topic),MODULE_CONTEXT)
                msg_count +=1
                log_info("*******************msg received count: {}; at {} ************".format(msg_count,datetime.datetime.now()),MODULE_CONTEXT)
                inputs = msg.value
                partition = msg.partition
                translation_batch = {}
                src_list, response_body = list(), list()

                if inputs is not None and all(v in inputs for v in ['message','record_id','id']) and len(inputs) is not 0:
                    try:
                        input_time = datetime.datetime.now()
                        log_info("Input for Record Id:{} at {}".format(inputs.get('record_id'),input_time),MODULE_CONTEXT)
                        log_info("Running batch-translation on  {}".format(inputs),MODULE_CONTEXT) 
                        record_id = inputs.get('record_id')
                        message = inputs.get('message')
                        src_list = [i.get('src') for i in message]
                        #translation_batch = {'id':inputs.get('id'),'src_list': src_list}
                        #output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
                        #Added for indic otherwise above two
                        model_id_v2 = get_model_id(inputs.get('source_language_code'), inputs.get('target_language_code'))
                        #translation_batch = {'id': model_id_v2, 'src_lang': inputs.get('source_language_code'),
                        #             'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
                        if "indic-indic" in model_id_v2:
                            output_batch, _, _ = KafkaTranslate_v2.get_pivoted_translation_response(inputs)
                        else:
                            #translation_batch = {'id': inputs.get('id'), 'src_lang': inputs.get('source_language_code'),
                            #             'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
                            #output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
                            #output_batch = FairseqDocumentTranslateService.many_to_many_translator(translation_batch)
                            output_batch, _, _ = KafkaTranslate_v2.get_translation_response(inputs, model_id_v2)
                        #End for indic2indic
                        log_info("Output of translation batch service at :{}".format(datetime.datetime.now()),MODULE_CONTEXT)                        
                        output_batch_dict_list = [{'tgt': output_batch['tgt_list'][i],
                                                'tagged_tgt':output_batch['tagged_tgt_list'][i],'tagged_src':output_batch['tagged_src_list'][i]}
                                                for i in range(len(message))]
                        
                        for j,k in enumerate(message):
                            k.update(output_batch_dict_list[j])
                            response_body.append(k)
                        
                        log_info("Record Id:{}; Final response body of current batch translation:{}".format(record_id,response_body),MODULE_CONTEXT) 
                        out = CustomResponse(Status.SUCCESS.value,response_body)   
                    except Exception as e:
                        status = Status.SYSTEM_ERR.value
                        status['message'] = str(e)
                        log_exception("Exception caught in batch_translator child block: {}".format(e),MODULE_CONTEXT,e) 
                        out = CustomResponse(status, inputs.get('message'))
                    
                    out = out.get_res_json()
                    out['record_id'] = record_id
                    log_info("Output for Record Id:{} at {}".format(record_id,datetime.datetime.now()),MODULE_CONTEXT)
                    log_info("Total time for processing Record Id:{} is: {}".format(record_id,(datetime.datetime.now()- input_time).total_seconds()),MODULE_CONTEXT)
                else:
                    status = Status.KAFKA_INVALID_REQUEST.value
                    out = CustomResponse(status, inputs.get('message'))
                    out = out.get_res_json()
                    if inputs.get('record_id'): out['record_id'] = inputs.get('record_id') 
                    log_info("Empty input request or key parameter missing in Batch translation request: batch_translator",MODULE_CONTEXT)      
            
                producer.send(producer_topic, value={'out':out},partition=partition)
                producer.flush()
                msg_sent += 1
                log_info("*******************msg sent count: {}; at {} **************".format(msg_sent,datetime.datetime.now()),MODULE_CONTEXT)
        except ValueError as e:  
            '''includes simplejson.decoder.JSONDecodeError '''
            log_exception("JSON decoding failed in KafkaTranslate-batch_translator method: {}".format(e),MODULE_CONTEXT,e)
            log_info("Reconnecting kafka c/p after exception handling",MODULE_CONTEXT)
            KafkaTranslate_v2.batch_translator(c_topic)  
        except Exception as e:
            log_exception("Exception caught in KafkaTranslate-batch_translator method: {}".format(e),MODULE_CONTEXT,e)
            log_info("Reconnecting kafka c/p after exception handling",MODULE_CONTEXT)
            KafkaTranslate_v2.batch_translator(c_topic)
            
            
    def get_translation_response(inputs, model_id):
        source_language_code, target_language_code = inputs.get('source_language_code'), inputs.get('target_language_code')

        # Check if the model supports the given lang-pair
        if not is_language_pair_supported(source_language_code, target_language_code, model_id):
            status = Status.UNSUPPORTED_LANGUAGE.value
            log_exception("kafka translate document | Unsupported input language code", MODULE_CONTEXT, status['message'])
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 400, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
        
        try:  
            log_info("Making kafka translate call", MODULE_CONTEXT)
            log_info("kafka translate  | input--- {}".format(inputs), MODULE_CONTEXT)
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
            log_info("Final output kafka translate call | {}".format(out.get_res_json()), MODULE_CONTEXT)     
            return out.get_res_json(), 200, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}   
        
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in kafka resource child block: {}".format(e), MODULE_CONTEXT, e) 
            out = CustomResponse(status, html_encode(inputs))
            return out.get_res_json(), 500, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}

    
    
    
    
    @staticmethod        
    def get_pivoted_translation_response(inputs, pivot_language_code="en"):
        source_language_code, target_language_code = inputs.get('source_language_code'), inputs.get('target_language_code')

        # First translate source to intermediate lang
        model_id = get_model_id(source_language_code, pivot_language_code)
        inputs["target_language_code"] = pivot_language_code
        response_json, status_code, http_headers = KafkaTranslate_v2.get_translation_response(inputs, model_id)
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
        response_json, status_code, http_headers = KafkaTranslate_v2.get_translation_response(intermediate_inputs, model_id)
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

