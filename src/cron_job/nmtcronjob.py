from threading import Thread

from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from config import nmt_cron_interval_sec
from config import translation_batch_limit, multi_lingual_batching_enabled
from resources import NMTTranslateResource_async, NMTTranslateResource_async_multilingual
from utilities import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception
import pandas as pd
import config
from repository import RedisRepo
from apscheduler.schedulers.background import BackgroundScheduler

redisclient = RedisRepo()


class NMTcronjob(Thread):
    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event

    # Cron JOB to fetch status of each record and push it to CH and WFM on completion/failure.
    def run(self):
        tranlate_utils = TranslateUtils()
        while not self.stopped.wait(nmt_cron_interval_sec):
            if multi_lingual_batching_enabled:
                tranlate_utils.translate_by_multilingual_batching()
            else:
                tranlate_utils.translate_by_lang_level_batching()


class TranslationScheduler:
    def __init__(self):
        pass

    def schedule(self):
        scheduler = BackgroundScheduler()
        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }
        tranlate_utils = TranslateUtils()
        if multi_lingual_batching_enabled:
            scheduler.add_job(func=tranlate_utils.translate_by_multilingual_batching, executors=executors, trigger="interval",
                              seconds=nmt_cron_interval_sec)
        else:
            scheduler.add_job(func=tranlate_utils.translate_by_lang_level_batching, executors=executors, trigger="interval",
                              seconds=nmt_cron_interval_sec)
        scheduler.start()


class TranslateUtils:
    def __init__(self):
        pass

    def translate_by_lang_level_batching(self):
        redis_data = []
        cron_id = config.get_cron_id()
        try:
            key_list = redisclient.get_all_keys()
            if key_list:
                values = redisclient.get_list_of_values(key_list)
                if values:
                    for rd_key in values.keys():
                        if 'translation_status' not in values[rd_key]:
                            redis_data.append((rd_key, values[rd_key]))
            if redis_data:
                log_info(f'CRON - {cron_id} Total Size of Redis Fetch: {len(redis_data)}', MODULE_CONTEXT)
                db_df = self.create_dataframe(redis_data)
                sample_json = redis_data[0][-1]
                del redis_data
                df_group = db_df.groupby(by=['modelid', 'src_language', 'tgt_language'])
                counter = 0
                for gb_key in df_group.groups.keys():
                    sub_df = df_group.get_group(gb_key)
                    sub_modelid = int(gb_key[0])
                    sub_src = str(gb_key[1])
                    sub_tgt = str(gb_key[2])
                    for i in range(0, sub_df.shape[0], translation_batch_limit):
                        sent_list = sub_df.iloc[i:i + translation_batch_limit].sentence.values.tolist()
                        db_key_list = sub_df.iloc[i:i + translation_batch_limit].db_key.values.tolist()
                        nmt_translator = NMTTranslateResource_async()
                        log_info(f"CRON - {cron_id} Translation started.....", MODULE_CONTEXT)
                        output = nmt_translator.async_call((sub_modelid, sub_src, sub_tgt, sent_list))
                        log_info(f"CRON - {cron_id} Translation COMPLETE!", MODULE_CONTEXT)
                        op_dict = {}
                        if output:
                            if 'tgt_list' in output:
                                for i, tgt_sent in enumerate(output['tgt_list']):
                                    sg_out = [{"source": sent_list[i], "target": tgt_sent}]
                                    sg_config = sample_json['config']
                                    final_output = {'config': sg_config, 'output': sg_out,
                                                    'translation_status': "Done"}
                                    op_dict[db_key_list[i]] = final_output
                            elif 'error' in output:
                                for i, _ in enumerate(sent_list):
                                    final_output = output['error']
                                    final_output['translation_status'] = 'Failure'
                                    op_dict[db_key_list[i]] = final_output
                            redisclient.bulk_upsert_redis(op_dict)
                            counter += 1
                log_info(f'CRON - {cron_id} Total no of BATCHES: {counter}', MODULE_CONTEXT)
        except Exception as e:
            log_exception("Async ULCA Batch Translation Cron-job | Exception in Cornjob: " + str(e), MODULE_CONTEXT, e)

    def translate_by_multilingual_batching(self):
        redis_data = []
        cron_id = config.get_cron_id()
        try:
            key_list = redisclient.get_all_keys()
            if key_list:
                values = redisclient.get_list_of_values(key_list)
                if values:
                    for rd_key in values.keys():
                        if 'translation_status' not in values[rd_key]:
                            redis_data.append((rd_key, values[rd_key]))
            if redis_data:
                log_info(f'CRON Total Size of Redis Fetch: {len(redis_data)}', MODULE_CONTEXT)
                db_df = self.create_dataframe(redis_data)
                sample_json = redis_data[0][-1]
                del redis_data
                counter = 0
                for batch_no, i in enumerate(range(0, db_df.shape[0], translation_batch_limit)):
                    sent_list = db_df.iloc[i:i + translation_batch_limit].sentence.values.tolist()
                    db_key_list = db_df.iloc[i:i + translation_batch_limit].db_key.values.tolist()
                    src_lang_list = db_df.iloc[i:i + translation_batch_limit].src_language.values.tolist()
                    tgt_lang_list = db_df.iloc[i:i + translation_batch_limit].tgt_language.values.tolist()
                    modelid_list = db_df.iloc[i:i + translation_batch_limit].modelid.values.tolist()
                    nmt_multilingual_translator = NMTTranslateResource_async_multilingual()
                    log_info(
                        f"CRON - {cron_id} translating via multilingual batching for Batch - {batch_no} & Batch size - {len(sent_list)}",
                        MODULE_CONTEXT)
                    output = nmt_multilingual_translator.async_call(
                        (modelid_list, src_lang_list, tgt_lang_list, sent_list))
                    log_info(f"CRON - {cron_id} translation via multilingual batching COMPLETED for Batch - {batch_no}",
                             MODULE_CONTEXT)
                    op_dict = {}
                    if output:
                        if 'tgt_list' in output:
                            for i, tgt_sent in enumerate(output['tgt_list']):
                                sg_out = [{"source": sent_list[i], "target": tgt_sent}]
                                sg_config = sample_json['config']
                                sg_config['modelId'] = modelid_list[i]
                                sg_config['language']['sourceLanguage'] = src_lang_list[i]
                                sg_config['language']['targetLanguage'] = tgt_lang_list[i]
                                final_output = {'config': sg_config, 'output': sg_out,
                                                'translation_status': "Done"}
                                op_dict[db_key_list[i]] = final_output
                        elif 'error' in output:
                            for i, _ in enumerate(sent_list):
                                final_output = output['error']
                                final_output['translation_status'] = 'Failure'
                                op_dict[db_key_list[i]] = final_output
                        redisclient.bulk_upsert_redis(op_dict)
                        counter += 1
                log_info(f'CRON - {cron_id} Total no of BATCHES: {counter}', MODULE_CONTEXT)
        except Exception as e:
            log_exception("Async ULCA Batch Translation Cron-job | Exception in Cornjob: " + str(e), MODULE_CONTEXT, e)

    def create_dataframe(self, redis_data):
        """Create and return dataframe from response of check_schema_ULCA function + redis_db key"""

        db_key_list, input_dict_list = zip(*redis_data)
        db_key_list = list(db_key_list)
        input_dict_list = list(input_dict_list)
        json_df = pd.json_normalize(input_dict_list, sep='_')
        json_df['input'] = json_df['input'].apply(lambda x: x[0]['source'])
        json_df['db_key'] = db_key_list
        json_df.rename(columns={'input': 'sentence',
                                'config_modelId': 'modelid',
                                'config_language_sourceLanguage': 'src_language',
                                'config_language_targetLanguage': 'tgt_language',
                                }, inplace=True)
        json_df = json_df.astype({'sentence': str, 'src_language': str, 'tgt_language': str, 'db_key': str},
                                 errors='ignore')
        return json_df
