import os

## Environment variables
IS_RUN_KAFKA = 'IS_RUN_KAFKA'
IS_RUN_KAFKA_DEFAULT_VALUE = False
bootstrap_server_boolean = os.environ.get(IS_RUN_KAFKA, IS_RUN_KAFKA_DEFAULT_VALUE)

KAFKA_BOOTSTRAP_SERVER_HOST = 'KAFKA_BOOTSTRAP_SERVER_HOST'
default_value = 'localhost:9092'
bootstrap_server = os.environ.get(KAFKA_BOOTSTRAP_SERVER_HOST, default_value)

## "description":"Kafka topics and variables"
nmt_input_topic_default = "aai4b-nmt-input-default"
nmt_output_topic_default = 'aai4b-nmt-output-default'
group_id_default = "aai4b-nmt-consumer-group"

group_id = os.environ.get('KAFKA_AAI4B_NMT_CONSUMER_GROUP', group_id_default)

kafka_topic = [
  {
    "consumer":os.environ.get('KAFKA_AAI4B_NMT_TRANSLATION_INPUT_TOPIC', nmt_input_topic_default),
    "producer":os.environ.get('KAFKA_AAI4B_NMT_TRANSLATION_OUTPUT_TOPIC', nmt_output_topic_default),
    "description":"kafka topics with WFM"
  }
]

