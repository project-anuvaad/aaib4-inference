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

class KafkaTranslate_v2:

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
                        translation_batch = {'id': model_id_v2, 'src_lang': inputs.get('source_language_code'),
                                     'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
                        #translation_batch = {'id': inputs.get('id'), 'src_lang': inputs.get('source_language_code'),
                        #             'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
                        #output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
                        output_batch = FairseqDocumentTranslateService.many_to_many_translator(translation_batch)
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
            KafkaTranslate.batch_translator(c_topic)  
        except Exception as e:
            log_exception("Exception caught in KafkaTranslate-batch_translator method: {}".format(e),MODULE_CONTEXT,e)
            log_info("Reconnecting kafka c/p after exception handling",MODULE_CONTEXT)
            KafkaTranslate.batch_translator(c_topic)        
    
