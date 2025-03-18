from flask import Flask
from .infrastructure.repository.DB import PostgresDB, AuthDB
import argparse
import os
import json
from .application.consumer import AuthConsumer # Modify to import specific blueprints

# function for creating database credential mappings
def parse_creds():
    # initialize Argument Parser
    parser = argparse.ArgumentParser(
        description='Performing validation on API spin up'
    )

    parser.add_argument('--username', type=str, help='Database username')
    parser.add_argument('--db_password', type=str, help='Database password')
    args = parser.parse_args()

    with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
        db_creds = json.load(f)
        db_creds['username'] = args.username
        db_creds['password'] = args.db_password

    return db_creds
    # parser.add_argument('--stripe_api_key', type=str, help='API key for Sripe transactions')
def create_app():
    app = Flask(__name__)

    # Initialize the connection pool
    cnn = '*DB CREDS*'
    PostgresDB.initialize_pool(cnn)

    
