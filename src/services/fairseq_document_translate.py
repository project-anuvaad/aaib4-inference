import os
import json
import sys
import re
import datetime
import torch
import functools

from anuvaad_auditor.loghandler import log_info, log_exception
import config

from services import load_models
from services import paragraph_sentence_tokenizer, dhruva_api
#from resources import translate_v2

from utilities import MODULE_CONTEXT
import utilities.fairseq_sentence_processor_v1 as sentence_processor_v1
import utilities.fairseq_sentence_processor_v2 as sentence_processor_v2

@functools.lru_cache(maxsize=None)
def get_src_and_tgt_langs_dict():
    with open(config.FETCH_MODEL_CONFG) as f:
        confs = json.load(f)
    
    id2version = {
        model["model_id"]: model["version"] if "version" in model else 1
        for model in confs["models"]
    }
    model_id2src_tgt = {
        model["model_id"]: (model["source_language_code"], model["source_language_code"])
        for model in confs["models"]
    }
    return model_id2src_tgt, id2version


class FairseqDocumentTranslateService:

    @staticmethod
    def batch_translator(input_dict):
        torch.cuda.empty_cache()
        model_id = input_dict["id"]
        src_list = input_dict["src_list"]
        num_sentence = len(src_list)
        out = {}

        translator = load_models.loaded_models[model_id]
        source_vocab = load_models.vocab[model_id][0]
        target_vocab = load_models.vocab[model_id][1]

        input_sentence_array_prepd = [None] * num_sentence

        model_id2src_tgt, id2version = get_src_and_tgt_langs_dict()

        try:
            for i, sent in enumerate(src_list):
                input_sentence_array_prepd[i] = sent
            log_info("translating using NMT-model:{}".format(model_id), MODULE_CONTEXT)

            if model_id in id2version:
                version = id2version[model_id]
                src_lang, tgt_lang = model_id2src_tgt[model_id]
                log_info(f"{src_lang}-{tgt_lang}", MODULE_CONTEXT)
                translation_array = encode_translate_decode(
                    input_sentence_array_prepd,
                    src_lang,
                    tgt_lang,
                    translator,
                    source_vocab,
                    target_vocab,
                    sentence_processor=sentence_processor_v2 if version >= 2 else sentence_processor_v1
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
    """   
    @staticmethod
    def indic_to_indic_translator(input_dict):
        torch.cuda.empty_cache()
        model_id = input_dict["id"]
        src_list = input_dict["src_list"]
        num_sentence = len(src_list)
        out = {}

        translator = load_models.loaded_models[model_id]
        source_vocab = load_models.vocab[model_id][0]

        input_sentence_array_prepd = [None] * num_sentence

        _, id2version = get_src_and_tgt_langs_dict()

        try:
            for i, sent in enumerate(src_list):   
                input_sentence_array_prepd[i] = sent
            log_info("translating using any to any NMT-model:{}".format(model_id), MODULE_CONTEXT)

            if model_id in id2version:
                src_lang, tgt_lang = (input_dict['src_lang'],input_dict['tgt_lang'])
                log_info("src_lang-{0},tgt_lang-{1}".format(src_lang,tgt_lang),MODULE_CONTEXT)
                translation_array = encode_translate_decode(
                    input_sentence_array_prepd,
                    src_lang,
                    tgt_lang,
                    translator,
                    source_vocab,
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
    """
    """
    #This indic to indic has been utilized for X-X, En-X, X-En, implemented on 21-03-2023, previously before 
    @staticmethod
    def many_to_many_translator(input_dict):
        torch.cuda.empty_cache()
        model_id = input_dict["id"]
        src_list = input_dict["src_list"]
        num_sentence = len(src_list)
        out = {}
        print("model_id.....", model_id)
        translator = load_models.loaded_models[model_id]
        source_vocab = load_models.vocab[model_id][0]
        target_vocab = load_models.vocab[model_id][1]

        input_sentence_array_prepd = [None] * num_sentence

        _, id2version = get_src_and_tgt_langs_dict()

        try:
            for i, sent in enumerate(src_list):   
                input_sentence_array_prepd[i] = sent
            log_info("translating using any to any NMT-model:{}".format(model_id), MODULE_CONTEXT)

            if model_id in id2version:
                version = id2version[model_id]
                src_lang, tgt_lang = input_dict['src_lang'], input_dict['tgt_lang']
                log_info("src_lang-{0},tgt_lang-{1}".format(src_lang,tgt_lang),MODULE_CONTEXT)
                translation_array = encode_translate_decode(
                    input_sentence_array_prepd,
                    src_lang,
                    tgt_lang,
                    translator,
                    source_vocab,
                    target_vocab,
                    sentence_processor=sentence_processor_v2 if version >= 2 else sentence_processor_v1
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
                "Exception caught in NMTTranslateService:indic_to_indic_translator:%s and %s"
                % (e, sys.exc_info()[0]),
                MODULE_CONTEXT,
                e,
            )
            raise e
            
        return out
        
    """
    #This many_to_many_translator works with Dhruva API, for local server please refere to above many_to_many_translator    
    @staticmethod
    def many_to_many_translator(input_dict):
        torch.cuda.empty_cache()
        model_id = input_dict["id"]
        src_list = input_dict["src_list"]
        num_sentence = len(src_list)
        out = {}
        print("model_id.....", model_id)
        #translator = load_models.loaded_models[model_id]
        #source_vocab = load_models.vocab[model_id][0]
        #target_vocab = load_models.vocab[model_id][1]

        input_sentence_array_prepd = [None] * num_sentence

        _, id2version = get_src_and_tgt_langs_dict()

        try:
            for i, sent in enumerate(src_list):   
                input_sentence_array_prepd[i] = sent
            log_info("translating using any to any NMT-model:{}".format(model_id), MODULE_CONTEXT)

            if model_id in id2version:
                version = id2version[model_id]
                src_lang, tgt_lang = input_dict['src_lang'], input_dict['tgt_lang']
                log_info("src_lang-{0},tgt_lang-{1}".format(src_lang,tgt_lang),MODULE_CONTEXT)
                """
                translation_array = encode_translate_decode(
                    input_sentence_array_prepd,
                    src_lang,
                    tgt_lang,
                    translator,
                    source_vocab,
                    target_vocab,
                    sentence_processor=sentence_processor_v2 if version >= 2 else sentence_processor_v1
                )
                """
                #Added for calling the dhruva api
                log_info("Dhruva API has been called: src_lang-{0},tgt_lang-{1}".format(src_lang,tgt_lang),MODULE_CONTEXT)
                translation_array = dhruva_api.dhruva_api_request(input_sentence_array_prepd, src_lang, tgt_lang)
                log_info("Dhruva API Call has been finished: {}".format(translation_array),MODULE_CONTEXT)
                #End
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
                "Exception caught in NMTTranslateService:indic_to_indic_translator:%s and %s"
                % (e, sys.exc_info()[0]),
                MODULE_CONTEXT,
                e,
            )
            raise e
            
        return out

"""
#The new encode_translate_decode for partial translation issue.
def encode_translate_decode(inputs, src_lang, tgt_lang, translator, source_vocab):
    #sent_count = []
    try:
        if src_lang == 'en':  
            inputs = [i.title() if i.isupper() else  i for i in inputs]
            inputs, sent_count = paragraph_sentence_tokenizer.sentence_tokenize_indic(inputs, src_lang)
        else:
            #new_inputs = inputs.copy()
            inputs, sent_count = paragraph_sentence_tokenizer.sentence_tokenize_indic(inputs, src_lang)           
        inputs = sentence_processor.preprocess(inputs, src_lang)
        inputs = apply_bpe(inputs, source_vocab)
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

#To handle the punctuation in the start and ending of the text.
def encode_translate_decode(inputs, src_lang, tgt_lang, translator, source_vocab, target_vocab, sentence_processor):
    my_punct = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '.',
           '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', 
           '`', '{', '|', '}', '~', '»', '«', '“', '”', '-']
    punct_pattern = re.compile("[" + re.escape("".join(my_punct)) + "]")
    punct_pattern_str = "".join(my_punct)
    start_punct_pattern = re.compile("^[" + re.escape("".join(my_punct)) + "]")
    end_punct_pattern = re.compile("[" + re.escape("".join(my_punct)) + "]$")
    try:
        if src_lang == 'en':  
            inputs = [i.title() if i.isupper() else  i for i in inputs]
        #newly added for punctuation
        punct_sen_index = []
        punct_in_sent = []
        punct_sen_index_last = []
        punct_in_sent_last = []
        punct_sen_index_ele1 = []
        for i, ele in enumerate(inputs):
            if len(ele) == 1:
                if 33 <= ord(ele) <= 47 or  58 <= ord(ele) <= 64 or 91 <= ord(ele) <= 96 or ord(ele) == 8221:
                    print("sentence contains only punctuation: {}".format(ele))
                    punct_sen_index_ele1.append(i)
            else:
                count_punct = 0
                for ch in ele:
                    if 33 <= ord(ch) <= 47 or  58 <= ord(ch) <= 64 or 91 <= ord(ch) <= 96:
                        count_punct += 1
                other_char = len(ele) - count_punct
                
                if count_punct > other_char:
                    
                    #If punctuations are in the beginning
                    if re.search(start_punct_pattern, ele) and not(re.search(end_punct_pattern, ele)):
                        print("punctuation start found", ele)
                        srt_ind = end_ind = 0
                        for j, ch in enumerate(ele):
                            if 48 <= ord(ch) <= 57 or  65 <= ord(ch) <= 90 or 97 <= ord(ch) <= 122:
                                break
                            end_ind = j
                        new_ele = ele.strip(punct_pattern_str)
                        inputs[i] = new_ele
                        punct_sen_index.append(i)
                        punct_in_sent.append(ele[0:end_ind+1])
                    #End of punctuation in the beginning
                
                    #If punctuations are in the end
                    if not(re.search(start_punct_pattern, ele)) and re.search(end_punct_pattern, ele):
                        print("punctuation end found", ele)
                        srt_ind = end_ind = 0
                        for j, ch in enumerate(ele):
                            if 33 <= ord(ch) <= 47 or  58 <= ord(ch) <= 64 or 91 <= ord(ch) <= 96:
                                break
                            srt_ind = j
                        srt_ind = srt_ind + 1
                        new_ele = ele.strip(punct_pattern_str)
                        inputs[i] = new_ele
                        punct_sen_index_last.append(i)
                        punct_in_sent_last.append(ele[srt_ind:])
                    #End of punctuation in the end
                #end for punctuation
        
        print("updated inputs:", inputs)
        preprocessed_inputs = sentence_processor.preprocess(inputs, src_lang)
        processed_inputs = sentence_processor.apply_vocab_processing(preprocessed_inputs, source_vocab)
        i_final = sentence_processor.apply_lang_tags(processed_inputs, src_lang, tgt_lang)
        i_final = truncate_long_sentences(i_final)
        translation = translator.translate(i_final)
        print(translation)
        translation = sentence_processor.postprocess(translation, tgt_lang, target_vocab, original_sents=inputs)
        #again postprocessing for punctuation
        punct_in_sent = sentence_processor.postprocess(punct_in_sent, tgt_lang, None)
        #For single element
        for k, el in enumerate(punct_sen_index_ele1):
            translation[el] = inputs[el]
        #For prefix part
        for k, el in enumerate(punct_sen_index):
            #translation[el] = inputs[el]
            translation[el] = punct_in_sent[k] + translation[el]
            print("Replacement in Prefix:",el, translation[el], inputs[el])
        #For suffix part
        for k, el in enumerate(punct_sen_index_last):
            #translation[el] = inputs[el]
            translation[el] =  translation[el] + punct_in_sent_last[k]
            print("Replacement in Sufffix:",el, translation[el], inputs[el])
        #end postprocessing
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
def encode_translate_decode(inputs, src_lang, tgt_lang, translator, source_vocab):
    try:
        if src_lang == 'en':  
            inputs = [i.title() if i.isupper() else  i for i in inputs]            
        inputs = sentence_processor.preprocess(inputs, src_lang)
        inputs = apply_bpe(inputs, source_vocab)
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

def truncate_long_sentences(sents):
    new_sents = []
    for sent in sents:
        num_words = len(sent.split())
        if num_words > config.trunc_limit:
            log_info("Sentence truncated as it exceeds maximum length limit of- {} tokens".format(config.trunc_limit),MODULE_CONTEXT)
            updated_sent = sent.split()[:config.trunc_limit]
            sent = str(" ".join(updated_sent)) 
        new_sents.append(sent)
    return new_sents        
