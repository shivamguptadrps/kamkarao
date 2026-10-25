#!/bin/sh
# Container start: apply database changes, make sure Banda base data exists, then serve.
set -e
python manage.py migrate --noinput
python manage.py seed_banda
python manage.py setup_roles
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${WEB_WORKERS:-3}" --timeout 30 --access-logfile -
