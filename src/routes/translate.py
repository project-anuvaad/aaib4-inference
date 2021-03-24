from flask import Blueprint
from flask_restful import Api
import config

from resources import NMTTranslateResource,InteractiveMultiTranslateResourceNew,TranslateResourceV1

TRANSLATE_BLUEPRINT = Blueprint("translate", __name__)


Api(TRANSLATE_BLUEPRINT).add_resource(
    NMTTranslateResource, config.MODULE_NAME + "/v0/translate"
)

Api(TRANSLATE_BLUEPRINT).add_resource(
    InteractiveMultiTranslateResourceNew, config.MODULE_NAME + "/v0/interactive-translation"
)

Api(TRANSLATE_BLUEPRINT).add_resource(
    TranslateResourceV1, config.MODULE_NAME + "/v1/translate"
)