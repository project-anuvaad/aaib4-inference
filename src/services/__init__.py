from .model_loader import Loadmodels
''' load_models pre-loads nmt variable and stores the translator object in a dictionary with keys being the model id'''
load_models = Loadmodels()
from .fairseq_translate import FairseqTranslateService, FairseqAutoCompleteTranslateService
from .fairseq_document_translate import FairseqDocumentTranslateService