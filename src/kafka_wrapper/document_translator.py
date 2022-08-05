from kafka_wrapper.producer import get_producer
from kafka_wrapper.consumer import get_consumer
from models import CustomResponse, Status
import config
import hashlib
from repository_redis import RedisRepo
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
import sys
import datetime
from services import FairseqDocumentTranslateService
from config import model_attention_score_tmx_enabled

redisclient = RedisRepo()

class KafkaTranslate:
                
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
                        translation_batch = {'id':inputs.get('id'),'src_list': src_list}
                        output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch, model_attention_score_tmx_enabled)
                        if 'token_maps' in output_batch.keys() and model_attention_score_tmx_enabled:
                            for i, src_sent in enumerate(src_list):
                                src_hash_key = hashlib.sha256(src_sent.encode('utf-16')).hexdigest()
                                src_hash_value = output_batch['token_maps'][i]
                                # print(output_batch['token_maps'][i])
                                redisclient.upsert_redis(src_hash_key, src_hash_value, True)
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
    