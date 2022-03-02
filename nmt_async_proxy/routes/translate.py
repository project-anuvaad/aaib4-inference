from flask import Blueprint
from flask_restful import Api
import config

from resources import NMTTranslateRedisWriteResource, NMTTranslateRedisReadResource, TranslationDummy

TRANSLATE_BLUEPRINT = Blueprint("translate", __name__)


Api(TRANSLATE_BLUEPRINT).add_resource(
    NMTTranslateRedisReadResource, config.MODULE_NAME + "/v0/" + config.model_to_load + "/search-translation"
)

Api(TRANSLATE_BLUEPRINT).add_resource(
    NMTTranslateRedisWriteResource, config.MODULE_NAME + "/v0/" + config.model_to_load + "/translate/async"
)

Api(TRANSLATE_BLUEPRINT).add_resource(
    TranslationDummy, config.MODULE_NAME + "/v0/" + config.model_to_load + "/translation/dummy"
)
