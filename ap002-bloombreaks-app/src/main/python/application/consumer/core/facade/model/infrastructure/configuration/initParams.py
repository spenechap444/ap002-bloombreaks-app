import json
import argparse
import os

class Config:

    def __init__(self):
        self.db_creds = self.parse_creds()

    database_config = {}

    def parse_creds(self):
        # initialize Argument Parser
        parser = argparse.ArgumentParser(
            description='Performing validation on API spin up'
        )
        parser.add_argument('--host', type=str)
        parser.add_argument('--port', type=str)
        args = parser.parse_args()

        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
            db_creds = json.load(f)['DB']
        
        db_creds['user'] = os.environ['DB_USERNAME']
        db_creds['password'] = os.environ['DB_PASSWORD']


        return db_creds

class DevelopmentConfig(Config):
    DEBUG=True

class ProductionConfig(Config):
    DEBUG=False
