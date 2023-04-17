import os
import json
import sys
import re
import datetime
import functools

from anuvaad_auditor.loghandler import log_info, log_exception

from models import CustomResponse, Status
from utilities import MODULE_CONTEXT
import config
from services import load_models
import utilities.fairseq_sentence_processor_v1 as sentence_processor_v1
import utilities.fairseq_sentence_processor_v2 as sentence_processor_v2

@functools.lru_cache(maxsize=None)
def get_src_and_tgt_langs_dict():
    model_id2src_tgt = {}
    # we have these two dictionaries to keep track of src-tgt lang pair to
    # corresponding model_id and constrained_model_id respectively
    src_tgt2model_id = {}
    src_tgt2constrained_model_id = {}
    with open(config.FETCH_MODEL_CONFG) as f:
        confs = json.load(f)
    models = confs["models"]
    id2version = {
        model["model_id"]: model["version"] if "version" in model else 1
        for model in confs["models"]
    }

    for model in models:
        model_id = model["model_id"]
        src_lang = model["source_language_code"]
        tgt_lang = model["target_language_code"]
        model_id2src_tgt[model_id] = (src_lang, tgt_lang)
        if model["is_constrained"]:
            src_tgt2constrained_model_id[(src_lang, tgt_lang)] = model_id
        else:
            src_tgt2model_id[(src_lang, tgt_lang)] = model_id

    for src_tgt in src_tgt2model_id.keys():
        # normal_model_id and constrained_model_id for a particular src and tgt
        # lang pair cannot be equal.
        assert src_tgt2model_id[src_tgt] != src_tgt2constrained_model_id[src_tgt]
    return model_id2src_tgt, id2version, src_tgt2constrained_model_id


class FairseqTranslateService:
    @staticmethod
    def simple_translation(inputs):
        out = {}
        i_src, tgt = list(), list()
        tagged_tgt = list()
        tagged_src = list()
        sentence_id = list()
        tp_tokenizer = None

        try:
            for i in inputs:
                sentence_id.append(i.get("s_id") or "NA")
                if any(v not in i for v in ["src", "id"]):
                    log_info("either id or src missing in some input", MODULE_CONTEXT)
                    out = CustomResponse(Status.ID_OR_SRC_MISSING.value, inputs)
                    return out

                log_info("input sentence:{}".format(i["src"]), MODULE_CONTEXT)
                i_src.append(i["src"])
                tag_src = i["src"]

                if i["id"] == 100:
                    "hindi-english"
                    translation = encode_translate_decode(i, "hi", "en")
                elif i["id"] == 101:
                    "bengali-english"
                    translation = encode_translate_decode(i, "bn", "en")
                elif i["id"] == 102:
                    "tamil-english"
                    translation = encode_translate_decode(i, "ta", "en")

                else:
                    log_info(
                        "unsupported model id: {} for given input".format(i["id"]),
                        MODULE_CONTEXT,
                    )
                    raise Exception(
                        "Unsupported Model ID - id: {} for given input".format(i["id"])
                    )

                tag_tgt = translation[0]
                log_info(
                    "simple translation-experiment-{} output: {}".format(
                        i["id"], translation
                    ),
                    MODULE_CONTEXT,
                )
                tgt.append(translation[0])
                tagged_tgt.append(tag_tgt)
                tagged_src.append(tag_src)

            out["response_body"] = [
                {
                    "tgt": tgt[i],
                    "tagged_tgt": tagged_tgt[i],
                    "tagged_src": tagged_src[i],
                    "s_id": sentence_id[i],
                    "src": i_src[i],
                }
                for i in range(len(tgt))
            ]
            out = CustomResponse(Status.SUCCESS.value, out["response_body"])
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status["why"] = str(e)
            log_exception(
                "Unexpected error:%s and %s" % (e, sys.exc_info()[0]), MODULE_CONTEXT, e
            )
            out = CustomResponse(status, inputs)

        return out


class FairseqAutoCompleteTranslateService:
    @staticmethod
    def constrained_translation(inputs):
        inputs = inputs
        out = {}
        sentence_id = list()
        i_src, tgt = list(), list()
        tagged_tgt, tagged_src = list(), list()
        (
            model_id2src_tgt,
            id2version,
            src_tgt2constrained_model_id,
        ) = get_src_and_tgt_langs_dict()
        try:
            for i in inputs:
                sentence_id.append(i.get("s_id") or "NA")
                if any(v not in i for v in ["src", "id"]):
                    log_info("either id or src missing in some input", MODULE_CONTEXT)
                    out = CustomResponse(Status.ID_OR_SRC_MISSING.value, inputs)
                    return out

                log_info("input sentences:{}".format(i["src"]), MODULE_CONTEXT)
                i_src.append(i["src"])
                tag_src = i["src"]

                model_id = i["id"]

                if model_id in id2version:
                    version = id2version[model_id]
                    if version < 2.0:
                        src_lang, tgt_lang = model_id2src_tgt[model_id]
                        constrained_model_id = src_tgt2constrained_model_id[
                            (src_lang, tgt_lang)
                        ]
                    else:
                        src_lang, tgt_lang = i["source_language_code"], i["target_language_code"]
                        constrained_model_id = model_id if model_id.endswith("/constrained") else model_id + "/constrained"
                    
                    if constrained_model_id not in id2version:
                        log_info(
                            "Constrained model id: {} not found for given input".format(constrained_model_id),
                            MODULE_CONTEXT,
                        )
                        raise Exception(
                            "Unsupported Constrained Model ID - id: {} for given input".format(constrained_model_id)
                        )
                    
                    print(f"{src_lang}-{tgt_lang}")
                    i["id"] = constrained_model_id
                    log_info("Calling itranslate function", MODULE_CONTEXT)
                    sentence_processor = sentence_processor_v2 if version >= 2 else sentence_processor_v1
                    translation = encode_itranslate_decode(i, src_lang, tgt_lang, sentence_processor)
                else:
                    log_info(
                        "Unsupported model id: {} for given input".format(i["id"]),
                        MODULE_CONTEXT,
                    )
                    raise Exception(
                        "Unsupported Model ID - id: {} for given input".format(i["id"])
                    )

                tag_tgt = translation
                log_info(
                    "translate_function-experiment-{} output: {}".format(
                        i["id"], translation
                    ),
                    MODULE_CONTEXT,
                )
                tgt.append(translation)
                tagged_tgt.append(tag_tgt), tagged_src.append(tag_src)

            out["response_body"] = [
                {
                    "tgt": tgt[i],
                    "s_id": sentence_id[i],
                    "src": i_src[i],
                    "tagged_tgt": tagged_tgt[i],
                    "tagged_src": tagged_src[i],
                }
                for i in range(len(tgt))
            ]
            out = CustomResponse(Status.SUCCESS.value, out["response_body"])
        except Exception as e:
            status = Status.SYSTEM_ERR.value
            status["message"] = str(e)
            log_exception(
                "Unexpected error:%s and %s" % (e, sys.exc_info()[0]), MODULE_CONTEXT, e
            )
            out = CustomResponse(status, inputs)

        return out


def encode_itranslate_decode(i, src_lang, tgt_lang, sentence_processor):
    try:
        inputs = [i["src"]]
        i["src"] = [i["src"]]
        i["target_prefix"] = [i["target_prefix"]]

        translator = load_models.loaded_models[i["id"]]
        source_vocab = load_models.vocab[i["id"]][0]
        target_vocab = load_models.vocab[i["id"]][1]
        i["src"] = sentence_processor.preprocess(i["src"], src_lang)
        i["src"] = sentence_processor.apply_vocab_processing(i["src"], source_vocab)
        # apply bpe to constraints with target bpe
        prefix = sentence_processor.apply_vocab_processing(i["target_prefix"], target_vocab)
        i_final = sentence_processor.apply_lang_tags(i["src"], src_lang, tgt_lang)
        translation = translator.translate(i_final, constraints=prefix)
        translation = sentence_processor.postprocess(translation, tgt_lang, target_vocab, original_sents=inputs)
        return translation

    except Exception as e:
        log_exception(
            "Unexpexcted error in encode_itranslate_decode: {} and {}".format(
                e, sys.exc_info()[0]
            ),
            MODULE_CONTEXT,
            e,
        )
        raise


def encode_translate_decode(i, src_lang, tgt_lang):
    try:
        i["src"] = [i["src"]]
        print(i["src"])
        translator = load_models.loaded_models[i["id"]]
        source_vocab = load_models.vocab[i["id"]][0]
        target_vocab = load_models.vocab[i["id"]][1]
        i["src"] = sentence_processor_v1.preprocess(i["src"], src_lang)
        i["src"] = sentence_processor_v1.apply_vocab_processing(i["src"], source_vocab)
        i_final = sentence_processor_v1.apply_lang_tags(i["src"], src_lang, tgt_lang)
        translation = translator.translate(i_final)
        translation = sentence_processor_v1.postprocess(translation, tgt_lang, target_vocab)
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
