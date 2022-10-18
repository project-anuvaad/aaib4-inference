from models import CustomResponse, Status
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
import os
import json
import sys
import re
import utilities.sentencepiece_util as sp
import utilities.fairseq_sentence_processor as sentence_processor
import config
import datetime
from services import load_models
from services import paragraph_sentence_tokenizer




def get_src_and_tgt_langs_dict():
    model_id2src_tgt = {}
    with open(config.FETCH_MODEL_CONFG) as f:
        confs = json.load(f)
        models = confs["models"]
        ids = [model["model_id"] for model in models]

    for model in models:
        model_id = model["model_id"]
        src_lang = model["source_language_code"]
        tgt_lang = model["target_language_code"]
        model_id2src_tgt[model_id] = (src_lang, tgt_lang)
    return model_id2src_tgt, ids


class FairseqDocumentTranslateService:
    @staticmethod
    def batch_translator(input_dict):
        model_id = input_dict["id"]
        src_list = input_dict["src_list"]
        num_sentence = len(src_list)
        tagged_src_list = [None] * num_sentence
        tagged_tgt_list = [None] * num_sentence
        tgt_list = [None] * num_sentence
        out = {}

        translator = load_models.loaded_models[model_id]
        source_bpe = load_models.bpes[model_id][0]
        # target_bpe = load_models.bpes[i["id"]][1]

        input_sentence_array_prepd = [None] * num_sentence

        model_id2src_tgt, ids = get_src_and_tgt_langs_dict()

        try:
            for i, sent in enumerate(src_list):
                    
                input_sentence_array_prepd[i] = sent
            log_info("translating using NMT-model:{}".format(model_id), MODULE_CONTEXT)

            if model_id in ids:
                src_lang, tgt_lang = model_id2src_tgt[model_id]
                print(f"{src_lang}-{tgt_lang}")
                translation_array = encode_translate_decode(
                    input_sentence_array_prepd,
                    src_lang,
                    tgt_lang,
                    translator,
                    source_bpe,
                )
            else:
                log_info(
                    "Unsupported model id: {} for given input".format(model_id),
                    MODULE_CONTEXT,
                )
                raise Exception(
                    "Unsupported Model ID - id: {} for given input".format(model_id)
                )

            out = {
                "tgt_list": translation_array,
                "tagged_src_list": input_sentence_array_prepd,
                "tagged_tgt_list": translation_array,
            }
        except Exception as e:
            log_exception(
                "Exception caught in NMTTranslateService:batch_translator:%s and %s"
                % (e, sys.exc_info()[0]),
                MODULE_CONTEXT,
                e,
            )
            raise e

        return out
    
    def indic_to_indic_translator(input_dict):
        model_id = input_dict["id"]
        src_list = input_dict["src_list"]
        num_sentence = len(src_list)
        out = {}

        translator = load_models.loaded_models[model_id]
        source_bpe = load_models.bpes[model_id][0]

        input_sentence_array_prepd = [None] * num_sentence

        _, ids = get_src_and_tgt_langs_dict()

        try:
            for i, sent in enumerate(src_list):   
                input_sentence_array_prepd[i] = sent
            log_info("translating using any to any NMT-model:{}".format(model_id), MODULE_CONTEXT)

            if model_id in ids:
                src_lang, tgt_lang = (input_dict['src_lang'],input_dict['tgt_lang'])
                log_info("src_lang-{0},tgt_lang-{1}".format(src_lang,tgt_lang),MODULE_CONTEXT)
                translation_array = encode_translate_decode(
                    input_sentence_array_prepd,
                    src_lang,
                    tgt_lang,
                    translator,
                    source_bpe,
                )
            else:
                log_info(
                    "Unsupported model id: {} for given input".format(model_id),
                    MODULE_CONTEXT,
                )
                raise Exception(
                    "Unsupported Model ID - id: {} for given input".format(model_id)
                )

            out = {
                "tgt_list": translation_array
            }
        except Exception as e:
            log_exception(
                "Exception caught in NMTTranslateService:indic_to_indic_translator:%s and %s"
                % (e, sys.exc_info()[0]),
                MODULE_CONTEXT,
                e,
            )
            raise e
            
        return out

#The new encode_translate_decode for partial translation issue.
def encode_translate_decode(inputs, src_lang, tgt_lang, translator, source_bpe):
    #sent_count = []
    try:
        if src_lang == 'en':  
            inputs = [i.title() if i.isupper() else  i for i in inputs]
            inputs, sent_count = paragraph_sentence_tokenizer.sentence_tokenize_indic(inputs, src_lang)
        else:
            #new_inputs = inputs.copy()
            inputs, sent_count = paragraph_sentence_tokenizer.sentence_tokenize_indic(inputs, src_lang)           
        inputs = sentence_processor.preprocess(inputs, src_lang)
        inputs = apply_bpe(inputs, source_bpe)
        i_final = sentence_processor.apply_lang_tags(inputs, src_lang, tgt_lang)
        i_final = truncate_long_sentences(i_final)
        translation = translator.translate(i_final)
        translation = sentence_processor.postprocess(translation, tgt_lang)
        return paragraph_sentence_tokenizer.sentence_detokenize_paragraph(translation, sent_count)
        
    except Exception as e:
        log_exception(
            "Unexpexcted error in encode_translate_decode: {} and {}".format(
                e, sys.exc_info()[0]
            ),
            MODULE_CONTEXT,
            e,
        )
        raise

"""
def encode_translate_decode(inputs, src_lang, tgt_lang, translator, source_bpe):
    try:
        if src_lang == 'en':  
            inputs = [i.title() if i.isupper() else  i for i in inputs]            
        inputs = sentence_processor.preprocess(inputs, src_lang)
        inputs = apply_bpe(inputs, source_bpe)
        i_final = sentence_processor.apply_lang_tags(inputs, src_lang, tgt_lang)
        i_final = truncate_long_sentences(i_final)
        translation = translator.translate(i_final)
        translation = sentence_processor.postprocess(translation, tgt_lang)
        return translation

    except Exception as e:
        log_exception(
            "Unexpexcted error in encode_translate_decode: {} and {}".format(
                e, sys.exc_info()[0]
            ),
            MODULE_CONTEXT,
            e,
        )
        raise

"""
def apply_bpe(sents, bpe):
    return [bpe.process_line(sent) for sent in sents]

def truncate_long_sentences(sents):
    new_sents = []
    for sent in sents:
        num_words = len(sent.split())
        print("---------------------------------------", sent, num_words)
        if num_words > config.trunc_limit:
            log_info("Sentence truncated as it exceeds maximum length limit of- {} tokens".format(config.trunc_limit),MODULE_CONTEXT)
            updated_sent = sent.split()[:config.trunc_limit]
            sent = str(" ".join(updated_sent)) 
        new_sents.append(sent)
    return new_sents        
