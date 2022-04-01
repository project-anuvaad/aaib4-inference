#!/bin/bash
python3 app.py
#gunicorn -w 4 --threads 4 -b 0.0.0.0:8003 "app:create_app_with_gunicorn()"