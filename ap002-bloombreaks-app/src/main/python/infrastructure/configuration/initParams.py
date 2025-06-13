import json
import argparse
import os


class Config:

    def __init__(self):
        self.db_creds = self.parse_creds()

    SECRET_KEY = 'XX'
    database_config = {}

    def parse_creds(self):
        # initialize Argument Parser
        parser = argparse.ArgumentParser(
            description='Performing validation on API spin up'
        )
        parser.add_argument('--host', type=str)
        parser.add_argument('--port', type=str)
        parser.add_argument('--db_username', type=str, help='Database username')
        parser.add_argument('--db_password', type=str, help='Database password')
        args = parser.parse_args()

        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
            db_creds = json.load(f)['DB']
            db_creds['user'] = args.username
            db_creds['password'] = args.db_password

        return db_creds

class DevelopmentConfig(Config):
    DEBUG=True

class ProductionConfig(Config):
    DEBUG=False
