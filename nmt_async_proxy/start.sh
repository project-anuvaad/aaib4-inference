#!/bin/bash
python3 app.py
# gunicorn -w 2 --threads 500 -b 0.0.0.0:5001 "app:create_app_with_gunicorn()"