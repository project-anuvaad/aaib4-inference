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
            self.model_path,
            self.dict_path,
            self.src_vocab_path,
            self.tgt_vocab_path,
            self.bpe_codes_path,
            self.ids,
        ) = self.get_paths()
        self.loaded_models = self.return_loaded_models(
            self.model_path, self.dict_path, self.ids
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
            model_path = models[0]["model_path"]
            dict_path = models[0]["dict_path"]
            src_vocab_path = models[0]["src_vocab_path"]
            tgt_vocab_path = models[0]["tgt_vocab_path"]
            bpe_codes_path = models[0]["bpe_codes_path"]
            ids = [model["model_id"] for model in models]
            return (
                model_path,
                dict_path,
                src_vocab_path,
                tgt_vocab_path,
                bpe_codes_path,
                ids,
            )

    def return_loaded_models(self, model_path, dict_path, ids):
        loaded_models = {}
        # since its a joint trained model, we initialize one model for all
        # ids
        translator = Translator(dict_path, model_path,batch_size=100)
        constrained_translator = Translator(
            dict_path, model_path, constrained_decoding=True,batch_size=100
        )
        for i, _ in enumerate(ids):
            if ids[i] in range(100, 104):
                loaded_models[ids[i]] = translator
            elif ids[i] in range(104, 107):
                loaded_models[ids[i]] = constrained_translator
            log_info("Model Loaded: {}".format(ids[i]), MODULE_CONTEXT)
        return loaded_models

    def return_models(self):
        return self.loaded_models
