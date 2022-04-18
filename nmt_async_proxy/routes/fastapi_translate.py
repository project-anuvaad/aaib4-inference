from fastapi import APIRouter, Body
from resources.translate import get_translation, write_to_fifo_redis, write_to_redis
import config 
from config import poll_api_interval_sec
import time
from config import MODULE_CONTEXT
from anuvaad_auditor.loghandler import log_info, log_exception, log_error
from models import CustomResponse, Status
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post('/trial')
async def update_item(
        payload = Body(...)
):
    return payload


@router.post("/"+config.MODULE_NAME + "/v0/" + config.model_to_load + "/search-translation")
async def redis_read(api_input = Body(...)):
    return get_translation(api_input)

@router.post("/"+config.MODULE_NAME + "/v0/" + config.model_to_load + "/translate/async")
async def redis_write(api_input = Body(...)):
    if config.use_redis_fifo_queue:
        return write_to_fifo_redis(api_input)
    else:
        return write_to_redis(api_input)

@router.post(config.MODULE_NAME + "/v0/" + config.model_to_load + "/translation/dummy")
async def dummy(api_input = Body(...)):

    log_info("Inside the dummy router", MODULE_CONTEXT) 

    if not isinstance( api_input, dict):
        log_exception("Non dict input recieved", MODULE_CONTEXT, e)
        try:
            return JSONResponse(status_code=500, content={'no_dict_error' : type(api_input)})
        except Exception as e:
            log_exception("Exception in isinstance of response while returning jsonresponse", MODULE_CONTEXT, e) 

    try:
        log_info("Inside the try block", MODULE_CONTEXT) 
        if config.use_redis_fifo_queue:
            response, code = write_to_fifo_redis(api_input)
        else:
            response, code = write_to_redis(api_input)
        if response:
            if 'requestId' in response.keys():
                request_id = response["requestId"]
                body = {"requestId": request_id}
                final_response = None
                while not final_response:
                    response, code = get_translation(body)
                    if response:
                        if "status" not in response.keys():
                            final_response = response
                    time.sleep(poll_api_interval_sec)
                # return final_response, 200
                # return JSONResponse(status_code=200, content=final_response)
                try:
                    return JSONResponse(status_code=200, content=final_response)
                except:
                   log_exception("Exception in if block of response while returning jsonresponse", MODULE_CONTEXT, e) 

            else:
                log_exception("No request ID in response", MODULE_CONTEXT, None)
                out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
                # return out.get_res_json_data(), 500
                try:
                    return JSONResponse(status_code=500, content=out.get_res_json_data())
                except:
                   log_exception("Exception in else block of response while returning jsonresponse", MODULE_CONTEXT, e) 

        else:
            log_exception("No response for search", MODULE_CONTEXT, None)
            out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
            # return out.get_res_json_data(), 500
            try:
                return JSONResponse(status_code=500, content=out.get_res_json_data())
            except Exception as e2:
               log_exception("exception in except block jsonresponse", MODULE_CONTEXT, e) 

    except Exception as e:
        log_exception("Something went wrong", MODULE_CONTEXT, e)
        out = CustomResponse(Status.SYSTEM_ERR.value, api_input)
        # return out.get_res_json_data(), 500
        try:
            return JSONResponse(status_code=500, content=out.get_res_json_data())
        except Exception as e2:
            log_exception("exception in except block jsonresponse", MODULE_CONTEXT, e2) 
        # return JSONResponse(status_code=500, content=out.get_res_json_data())
