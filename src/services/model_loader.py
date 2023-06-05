import config
import json
import os
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
from services.model_vocab_loader_v2 import TranslatorV2, load_vocab_v2
#from services.model_vocab_loader_v1 import TranslatorV1, load_vocab_v1


class Loadmodels:
    """
    Load nmt models while starting the application
    Returns a dictionary of model id and model object(based on ctranslate2)
    """

    def __init__(self):
        log_info("Pre-loading NMT models at startup", MODULE_CONTEXT)
        (
            self.model_paths,
            self.dict_paths,
            self.src_vocab_paths,
            self.tgt_vocab_paths,
            self.src_bpe_codes_path,
            self.tgt_bpe_codes_path,
            self.ids,
            self.is_constrained,
            self.versions,
        ) = self.get_paths()
        self.loaded_models = self.return_loaded_models(
            self.model_paths, self.dict_paths, self.ids, self.is_constrained, self.versions,
        )
        self.vocab = {}
        for _id, version, src_vocab_path, tgt_vocab_path, src_bpe_codes_path, tgt_bpe_codes_path in zip(
            self.ids, self.versions, self.src_vocab_paths, self.tgt_vocab_paths, self.src_bpe_codes_path,self.tgt_bpe_codes_path
        ):
            if version < 2.0:
                source_bpe = load_vocab_v1(src_vocab_path, src_bpe_codes_path)
                target_bpe = load_vocab_v1(tgt_vocab_path, tgt_bpe_codes_path)
                self.vocab[_id] = [source_bpe, target_bpe]
            else:
                source_spm = load_vocab_v2(src_vocab_path)
                target_spm = load_vocab_v2(tgt_vocab_path)
                self.vocab[_id] = [source_spm, target_spm]

    def get_paths(self):
        with open(config.FETCH_MODEL_CONFG) as f:
            confs = json.load(f)
            models = [model for model in confs["models"] if "disabled" not in model or not model["disabled"]]
            model_paths = [model["model_path"] for model in models]
            dict_paths = [model["dict_path"] for model in models]
            src_vocab_paths = [model["src_vocab_path"] for model in models]
            tgt_vocab_paths = [model["tgt_vocab_path"] for model in models]
            src_bpe_codes_path = [model["src_bpe_codes_path"] for model in models]
            tgt_bpe_codes_path = [model["tgt_bpe_codes_path"] for model in models]
            ids = [model["model_id"] for model in models]
            is_constrained = [model["is_constrained"] for model in models]
            versions = [model["version"] if "version" in model else 1 for model in models]
            return (
                model_paths,
                dict_paths,
                src_vocab_paths,
                tgt_vocab_paths,
                src_bpe_codes_path,
                tgt_bpe_codes_path,
                ids,
                is_constrained,
                versions,
            )

    def return_loaded_models(self, model_paths, dict_paths, ids, is_constrained_list, versions):
        loaded_models = {}
        # this has key of (model_path, dict_path) and stores the corresponding translation model
        params2translator = {}
        # this has key of (model_path, dict_path) and stores the corresponding constrained model
        params2cons_translator = {}
        for i, _ in enumerate(ids):
            dict_path = dict_paths[i]
            model_path = model_paths[i]
            param = (model_path, dict_path)
            TranslatorClass = TranslatorV1 if versions[i] < 2.0 else TranslatorV2
            
            if is_constrained_list[i]:
                if params2cons_translator.get(param, None):
                    constrained_translator = params2cons_translator[param]
                else:
                    # TODO: Make `batch_size` a config parameter
                    constrained_translator = TranslatorClass(
                        dict_path, model_path, constrained_decoding=True, batch_size=100
                    )
                    params2cons_translator[param] = constrained_translator
                loaded_models[ids[i]] = constrained_translator
            
            else:
                if params2translator.get(param, None):
                    translator = params2translator[param]
                else:
                    # TODO: Make `batch_size` a config parameter
                    translator = TranslatorClass(dict_path, model_path, batch_size=100)
                    params2translator[param] = translator
                loaded_models[ids[i]] = translator
            
            log_info("Model Loaded- base: {} with constraint:{}".format(ids[i], is_constrained_list[i]), MODULE_CONTEXT)
        return loaded_models

    def return_models(self):
        return self.loaded_models
