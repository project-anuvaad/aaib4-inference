#!/bin/bash
# python3 app.py
gunicorn -w 100 --threads 10 -b 0.0.0.0:5001 "app:create_app_with_gunicorn()"