"""WSGI entry for production servers (gunicorn/uwsgi)."""
from app import create_app

app = create_app()
