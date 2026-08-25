import json
import os

class Config:

    def __init__(self):
        self.db_creds = self.parse_creds()

    database_config = {}

    def parse_creds(self):
        # config.json holds local-dev defaults (host.docker.internal, bloombreaks-dev);
        # env vars override them so the same image runs anywhere.
        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
            db_creds = json.load(f)['DB']

        db_creds['host'] = os.environ.get('DB_HOST', db_creds['host'])
        db_creds['port'] = int(os.environ.get('DB_PORT', db_creds['port']))
        db_creds['database'] = os.environ.get('DB_NAME', db_creds['database'])

        # No defaults for credentials - fail fast at startup if they're missing.
        db_creds['user'] = os.environ['DB_USERNAME']
        db_creds['password'] = os.environ['DB_PASSWORD']

        return db_creds

class DevelopmentConfig(Config):
    DEBUG=True

class ProductionConfig(Config):
    DEBUG=False
