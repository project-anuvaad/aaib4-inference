from threading import Thread
from config import nmt_cron_interval_ms
from config import translation_batch_limit
from resources import NMTTranslateResource_async
from utilities import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception
import json
import pandas as pd
import redis
from config import redis_server_host, redis_server_port, redis_server_pass, redis_db, record_expiry_in_sec

redis_client_datasets = None


class NMTcronjob(Thread):
    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event

    # Cron JOB to fetch status of each record and push it to CH and WFM on completion/failure.
    def run(self):
        run = 0
        log_info("Getting redis instance.....", MODULE_CONTEXT)
        redis_client = get_redis_instance()
        log_info("Redis instance created.....", MODULE_CONTEXT)
        # print(nmt_cron_interval_ms)
        while not self.stopped.wait(0.5):
            try:
                log_info("CRON EXECUTING.....", MODULE_CONTEXT)
                redis_data = []
                key_list = redis_client.keys()
                if key_list:
                    for rd_key in key_list:
                        value = json.loads(redis_client.get(rd_key))
                        if 'translation_status' not in value:
                            redis_data.append((rd_key, value))
                if redis_data:
                    db_df = self.create_dataframe(redis_data)
                    del redis_data
                    '''
                    #Pushing response for request with wrong schema
                    for entry_indx in db_df[db_df.schema == False].index:
                        db_key = db_df.last[entry_indx,'db_key']
                        log_info("ULCA Async API input missing mandatory data ('input','config,'modelId', 'language')",MODULE_CONTEXT)
                        status = Status.INVALID_API_REQUEST.value
                        status['message'] = "Missing mandatory data ('input','config','modelId, 'language')"
                        status['translation_status'] = "Done"
                        redis_client.upsert(db_key, status)
                    # Deleting wrong schema entries from dataframe
                    db_df.drop(db_df[db_df.schema == False].index, inplace = True)
                    '''
                    # Creating groups based on modelid,src,tgt lauage
                    df_group = db_df.groupby(by=['modelid', 'src_language', 'tgt_language'])
                    for gb_key in df_group.groups.keys():
                        sub_df = df_group.get_group(gb_key)
                        sub_modelid = int(gb_key[0])
                        sub_src = str(gb_key[1])
                        sub_tgt = str(gb_key[2])

                        for i in range(0, sub_df.shape[0], translation_batch_limit):
                            sent_list = sub_df.iloc[i:i + translation_batch_limit].sentence.values.tolist()
                            db_key_list = sub_df.iloc[i:i + translation_batch_limit].db_key.values.tolist()
                            nmt_translator = NMTTranslateResource_async()
                            output = nmt_translator.async_call((sub_modelid, sub_src, sub_tgt, sent_list))
                            sample_json = sub_df.iloc[0].input

                            if 'tgt_list' in output:
                                for i, tgt_sent in enumerate(output['tgt_list']):
                                    sg_out = [{"source": sent_list[i], "target": tgt_sent[i]}]
                                    sg_config = sample_json['config']
                                    final_output = {'config': sg_config, 'output': sg_out, 'translation_status': "Done"}
                                    log_info(
                                        "Final output from Async call for ULCA batch translation pushed on redis for a "
                                        "request : {}".format(
                                            final_output), MODULE_CONTEXT)
                                    upsert(str(db_key_list[i]), final_output, True)
                            elif 'error' in output:
                                for i, _ in enumerate(sent_list):
                                    final_output = output['error']
                                    final_output['translation_status'] = 'Done'
                                    upsert(str(db_key_list[i]), final_output, True)
                    run += 1
                    log_info("Async NMT Batch Translation Cron-job" + " -- Run: " + str(run) + " | Cornjob Completed",
                             MODULE_CONTEXT)
                else:
                    run += 1
                    log_info("No Requests available in REDIS --- Run: {} | Cornjob Completed".format(run),
                             MODULE_CONTEXT)
            except Exception as e:
                run += 1
                log_exception("Async ULCA Batch Translation Cron-job" + " -- Run: " + str(
                    run) + " | Exception in Cornjob: " + str(e), e, e)

    def check_schema_ULCA(self, json_ob):
        """Check if post request matches the schema for ULCA Translation
            Also returns a list of post request data, schema match(True/False),
            sentence, modelid, source and target language"""

        if len(json_ob) > 0 and all(v in json_ob for v in ['input', 'config']) and \
                all(m in json_ob.get('config') for m in ['modelId', 'language']):
            if all(j in json_ob.get('config')['language'] for j in ['sourceLanguage', 'targetLanguage']) and \
                    'source' in json_ob.get('input')[0]:
                json_language = json_ob.get('config')['language']
                return [json_ob, True, json_ob.get('input')[0]['source'], json_ob.get('config')['modelId'],
                        json_language['sourceLanguage'], json_language['targetLanguage']]
        return [json_ob, False, None, None, None, None]

    def create_dataframe(self, redis_data):
        """Create and return dataframe from response of check_schema_ULCA function + redis_db key"""

        json_df = pd.DataFrame(
            columns=['input', 'schema', 'sentence', 'modelid', 'src_language', 'tgt_language', 'db_key'])
        for key, value in redis_data:
            # chk = self.check_schema_ULCA(value)
            value_language = value.get('config')['language']
            chk = [value, True, value.get('input')[0]['source'], value.get('config')['modelId'],
                        value_language['sourceLanguage'], value_language['targetLanguage']]
            chk.append(key)
            json_df.loc[len(json_df)] = chk
        json_df = json_df.astype({'sentence': str, 'db_key': str, 'src_language': str, 'tgt_language': str},
                                 errors='ignore')
        return json_df


def redis_instantiate():
    global redis_client_datasets
    redis_client_datasets = redis.Redis(host=redis_server_host, port=redis_server_port, db=redis_db,
                                        password=redis_server_pass)
    return redis_client_datasets


def get_redis_instance():
    global redis_client_datasets
    if not redis_client_datasets:
        return redis_instantiate()
    else:
        return redis_client_datasets


def upsert(key, value, expiry):
    try:
        client = get_redis_instance()
        if expiry:
            client.set(key, json.dumps(value), ex=record_expiry_in_sec)
        else:
            client.set(key, json.dumps(value))
        return True
    except Exception as e:
        log_exception(f'Exception in redis upsert: {e}', MODULE_CONTEXT, e)
        return None


def search_redis(key):
    try:
        client = get_redis_instance()
        result = []
        val = client.get(key)
        if val:
            result.append(json.loads(val))
        return result
    except Exception as e:
        log_exception(f'Exception in redis search: {e}', MODULE_CONTEXT, e)
        return None
