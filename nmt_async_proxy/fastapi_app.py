# import imp
import uvicorn
from fastapi import FastAPI
from fastapi import APIRouter, Body
from cron_job import NMTcronjob, NMTcronjob_subprocess
import threading
from fastapi.middleware.cors import CORSMiddleware
import routes
import config
from anuvaad_auditor.loghandler import log_info
from config import MODULE_CONTEXT
import multiprocessing

# from routes.translate import router

app = FastAPI(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


if __name__ == "__main__":
    log_info('starting cronjob', MODULE_CONTEXT)
    if config.use_redis_fifo_queue:
        wfm_jm_subprocess = multiprocessing.Process(target=NMTcronjob_subprocess.run, name='cronjob_subprocess')
        wfm_jm_subprocess.start()
    else:
        wfm_jm_thread = NMTcronjob(threading.Event())
        wfm_jm_thread.start()
        
    log_info('starting FastApi', MODULE_CONTEXT)
    uvicorn.run(
        "fastapi_app:app", host=config.HOST, port=config.PORT,  reload=False
    )


if config.use_fast_api_gunicorn:
    log_info('starting cronjob', MODULE_CONTEXT)
    if config.use_redis_fifo_queue:
        log_info('starting cronjob subprocess', MODULE_CONTEXT)
        wfm_jm_gu_subprocess = multiprocessing.Process(target=NMTcronjob_subprocess.run, name='cronjob_subprocess')
        wfm_jm_gu_subprocess.start()
    else:
        log_info('starting cronjob threaded', MODULE_CONTEXT)
        wfm_jm_gu_thread = NMTcronjob(threading.Event())
        wfm_jm_gu_thread.start()
else:
    log_info('FastAPI enviroment variable set to False', MODULE_CONTEXT) 
