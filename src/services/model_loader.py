import config
import json
import os
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
from services.model_vocab_loader import Translator, load_vocab


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
            self.bpe_codes_paths,
            self.ids,
        ) = self.get_paths()
        self.loaded_models = self.return_loaded_models(
            self.model_paths, self.dict_paths, self.ids
        )
        self.bpes = {}
        source_bpe = load_vocab(self.src_vocab_path, self.bpe_codes_path)
        target_bpe = load_vocab(self.tgt_vocab_path, self.bpe_codes_path)
        for _id in self.ids:
            self.bpes[_id] = [source_bpe, target_bpe]

    def get_paths(self):
        with open(config.FETCH_MODEL_CONFG) as f:
            confs = json.load(f)
            models = confs["models"]
            model_path = [model["model_path"] for model in models]
            dict_path = [model["dict_path"] for model in models]
            src_vocab_path = [model["src_vocab_path"] for model in models]
            tgt_vocab_path = [model["tgt_vocab_path"] for model in models]
            bpe_codes_path = [model["bpe_codes_path"] for model in models]
            ids = [model["model_id"] for model in models]
            return (
                model_path,
                dict_path,
                src_vocab_path,
                tgt_vocab_path,
                bpe_codes_path,
                ids,
            )

    def return_loaded_models(self, model_paths, dict_paths, ids):
        loaded_models = {}
        # this has key of (model_path, dict_path) and stores the corresponding translation model
        params2translator = {}
        # this has key of (model_path, dict_path) and stores the corresponding constrained model
        params2cons_translator = {}
        for i, _ in enumerate(ids):
            dict_path = dict_paths[i]
            model_path = dict_paths[i]
            param = (model_path, dict_path)
            if params2translator.get(param, None):
                translator = params2translator[param]
                constrained_translator = params2cons_translator[param]
            else:
                translator = Translator(dict_path, model_path, batch_size=100)
                constrained_translator = Translator(
                    dict_path, model_path, constrained_decoding=True, batch_size=100
                )
                params2translator[param] = translator
                params2cons_translator[param] = constrained_translator
            if ids[i] in range(100, 104):
                loaded_models[ids[i]] = translator
            elif ids[i] in range(104, 107):
                loaded_models[ids[i]] = constrained_translator
            log_info("Model Loaded: {}".format(ids[i]), MODULE_CONTEXT)
        return loaded_models

    def return_models(self):
        return self.loaded_models
