#!/bin/bash
# python3 app.py
gunicorn -w 10 --threads 100 -b 0.0.0.0:5001 "app:create_app_with_gunicorn()"