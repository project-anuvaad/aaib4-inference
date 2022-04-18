#!/bin/bash
python3 app.py
# python3 fastapi_app.py
# gunicorn -w 10 --threads 100 -b 0.0.0.0:5001 "app:create_app_with_gunicorn()"
# gunicorn -w 2 --worker-class uvicorn.workers.UvicornWorker -b 0.0.0.0:5001 fastapi_app:app