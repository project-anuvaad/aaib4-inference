from kafka_wrapper.producer import get_producer
from kafka_wrapper.consumer import get_consumer
from kafka.admin import KafkaAdminClient, NewTopic
from models import CustomResponse, Status
import config
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
import sys
import datetime
from services import FairseqDocumentTranslateService, FairseqAutoCompleteTranslateService

import json
from flask_restful import Resource
from flask import request
from html import escape
import functools
import threading, queue

message_queue = queue.Queue()
producer = get_producer()

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

def process_message(msg):
    producer_topic = [topic["producer"] for topic in config.kafka_topic if topic["consumer"] == msg.topic][0]
    log_info("Producer for current consumer:{} is-{}".format(msg.topic,producer_topic),MODULE_CONTEXT)
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
            #src_list = [i.get('src') for i in message]
            #translation_batch = {'id':inputs.get('id'),'src_list': src_list}
            #output_batch = FairseqDocumentTranslateService.batch_translator(translation_batch)
            #Added for indic otherwise above two
            model_id_v2 = get_model_id(inputs.get('source_language_code'), inputs.get('target_language_code'))
            #translation_batch = {'id': model_id_v2, 'src_lang': inputs.get('source_language_code'),
            #             'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
            """
            if "indic-indic" in model_id_v2:
                output_batch, status_code, _ = KafkaTranslate_v2.get_pivoted_translation_response(inputs)
                log_info("Translation response in kafka batch translator v2, in-in, status: {}".format(status_code),MODULE_CONTEXT)
            else:
                #translation_batch = {'id': inputs.get('id'), 'src_lang': inputs.get('source_language_code'),
                #             'tgt_lang': inputs.get('target_language_code'), 'src_list': src_list}
                #output_batch = FairseqDocumentTranslateService.indic_to_indic_translator(translation_batch)
                #output_batch = FairseqDocumentTranslateService.many_to_many_translator(translation_batch)
                output_batch, status_code, _ = KafkaTranslate_v2.get_translation_response(inputs, model_id_v2)
                log_info("Translation response in kafka batch translator v2, en-in, status: {}".format(status_code),MODULE_CONTEXT)
            """
            output_batch, status_code, _ = KafkaTranslate_v2.get_translation_response(inputs, model_id_v2)
            log_info("Translation response in kafka batch translator v2, src_lang-{0},tgt_lang-{1}, status: {2}".format(inputs.get('source_language_code'), inputs.get('target_language_code'), status_code),MODULE_CONTEXT)
            #End for indic2indic
            log_info("Output of translation batch service at :{}".format(datetime.datetime.now()),MODULE_CONTEXT)
            time_taken =  datetime.datetime.now() - input_time
            #time_taken.total_seconds() 
            log_info("Total time taken in this batch translation :{}".format(time_taken.total_seconds()),MODULE_CONTEXT)                 
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

    log_info(f"Pushing information to topic {producer_topic} and partition {partition}",MODULE_CONTEXT)
    producer.send(producer_topic, value={'out':out},partition=partition)
    producer.flush()

# Thread worker function
def message_consumer():
    while True:
        # Get a message from the queue
        message = message_queue.get()
        # Process the message
        process_message(message)
        # Mark the message as processed
        message_queue.task_done()

# Create multiple consumer threads
num_threads = 4  # Number of threads to process messages
for _ in range(num_threads):
    t = threading.Thread(target=message_consumer)
    t.daemon = True  # Threads will exit when the main thread exits
    t.start()
    
# Wait for all messages to be processed
message_queue.join()

class KafkaTranslate_v2:

    @staticmethod
    def create_topics(topic_names,consumer):
        admin_client = KafkaAdminClient(
                        bootstrap_servers=config.kafka_topics.bootstrap_server, 
                        client_id='test'
                    )
        existing_topic_list = consumer.topics()
        print("EXISTING TOPICS:",list(consumer.topics()))
        topic_list = []
        for topic in topic_names:
            if topic not in existing_topic_list:
                print('Topic : {} added '.format(topic))
                topic_list.append(NewTopic(name=topic, num_partitions=6, replication_factor=1))
            else:
                print('Topic : {} already exist '.format(topic))
        try:
            if topic_list:
                admin_client.create_topics(new_topics=topic_list, validate_only=False)
                print("Topic Created Successfully")
            else:
                print("Topic Exist")
        except  Exception as e:
            print(e)

    @staticmethod
    def batch_translator(c_topic):
        ''' New method for batch translation '''      
        log_info('KafkaTranslate: batch_translator',MODULE_CONTEXT)  
        out = {}
        msg_count,msg_sent = 0,0
        consumer = get_consumer(c_topic)
        producer = get_producer()
        list_of_topics = [config.kafka_topic[0]['consumer'],config.kafka_topic[0]['producer']]
        KafkaTranslate_v2.create_topics(list_of_topics,consumer)
        try:
            for msg in consumer:
                msg_count+=1
                log_info("*******************msg received count: {}; at {} ************".format(msg_count,datetime.datetime.now()),MODULE_CONTEXT)
                message_queue.put(msg)
                msg_sent+=1
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
            #out = CustomResponse(status, html_encode(inputs))
            out = CustomResponse(status, inputs.get('message'))
            return out.get_res_json(), 400, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
        
        try:  
            log_info("Making kafka translate call", MODULE_CONTEXT)
            log_info("kafka translate  | input--- {}".format(inputs), MODULE_CONTEXT)
            #input_src_list = inputs.get('src_list')
            message = inputs.get('message')
            #src_list = [i.get('src') for i in message]
            translation_batch = {
                'id': model_id,
                'src_lang': source_language_code,
                'tgt_lang': target_language_code,
                #'src_list': src_list
                'src_list': [item.get('src') for item in message],
            }
            output_batch = FairseqDocumentTranslateService.many_to_many_translator(translation_batch)
            return output_batch, 200, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
		
            # Stitch the translated sentences along with source sentences
            """
            response_body = []
            for i, item in enumerate(message):
                item.update(
                    {'tgt': output_batch['tgt_list'][i]}
                )
                response_body.append(item)
            
            # Construct output payload
            out = CustomResponse(Status.SUCCESS.value, response_body) 
            log_info("Final output kafka translate call | {}".format(out.get_res_json()), MODULE_CONTEXT)     
            return out.get_res_json(), 200, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}   
            """
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status['message'] = str(e)
            log_exception("Exception caught in kafka resource child block: {}".format(e), MODULE_CONTEXT, e) 
            #out = CustomResponse(status, html_encode(inputs))
            out = CustomResponse(status, inputs.get('message'))
            return out.get_res_json(), 500, {'Content-Type': DEFAULT_CONTENT_TYPE, 'X-Content-Type-Options': 'nosniff'}
            #return out.get_res_json()

    
    
    
    
    @staticmethod        
    def get_pivoted_translation_response(inputs, pivot_language_code="en"):
        source_language_code, target_language_code = inputs.get('source_language_code'), inputs.get('target_language_code')

        # First translate source to intermediate lang
        model_id = get_model_id(source_language_code, pivot_language_code)
        inputs["target_language_code"] = pivot_language_code
        response_json, status_code, http_headers = KafkaTranslate_v2.get_translation_response(inputs, model_id)
        #response_json = KafkaTranslate_v2.get_translation_response(inputs, model_id)
        if status_code != 200:
            # If error, just return it directly
            return response_json, status_code, http_headers

        # Now use intermediate translations as source
        intermediate_inputs = {
            "source_language_code": pivot_language_code,
            "target_language_code": target_language_code,
            "message": [{"src": response_json['tgt_list'][i]} for i in range(len(response_json['tgt_list']))]
            #"message": [{"src": item["tgt"]} for item in response_json["data"]],
        }
        model_id = get_model_id(pivot_language_code, target_language_code)
        response_json, status_code, http_headers = KafkaTranslate_v2.get_translation_response(intermediate_inputs, model_id)
        #response_json = KafkaTranslate_v2.get_translation_response(intermediate_inputs, model_id)
        if status_code != 200:
            # If error, just return it directly
            return response_json, status_code, http_headers

        # Put original source sentences back and send the response
        src_list = []
        for i, item in enumerate(inputs["message"]):
            #response_json["data"][i]["src"] = item["src"]
            src_list.append(item['src'])
        response_json["tagged_src_list"] = src_list
        return response_json, status_code, http_headers
        #return response_json
        

def html_encode(request_json_obj):
    try:
        request_json_obj["source_language_code"] = escape(request_json_obj["source_language_code"])
        request_json_obj["target_language_code"] = escape(request_json_obj["target_language_code"])
        #for item in request_json_obj['src_list']:
        for item in request_json_obj['message']:
            item['src'] = escape(item['src'])
    except Exception as e:
        log_exception("Exception caught in v2 translate API html encoding: {}".format(e),MODULE_CONTEXT,e)

    return request_json_obj

