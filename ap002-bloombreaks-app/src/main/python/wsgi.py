from main import create_app

# Gunicorn entry point: gunicorn wsgi:application
application = create_app('production')
