#!/usr/bin/env sh
set -e

python manage.py migrate --noinput || true
python manage.py collectstatic --noinput || true

python manage.py runserver 0.0.0.0:8000
