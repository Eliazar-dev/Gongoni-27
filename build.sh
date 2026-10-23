#!/bin/bash
python -m pip install -r requirements.txt
cd backend
python manage.py collectstatic --noinput
