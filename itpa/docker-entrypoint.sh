#!/bin/bash

# Wait for the database server to come up
sleep 4

python manage.py makemigrations itpa
python manage.py migrate

gunicorn itpa.wsgi:application -w 2 -b :8060 --reload
