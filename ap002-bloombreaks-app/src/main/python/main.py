from flask import Flask
from .infrastructure.repository.DB import PostgresDB, AuthDB
from .application.consumer import AuthConsumer # Modify to import specific blueprints


def create_app():
    app = Flask(__name__)

    # Initialize the connection pool
    cnn = '*DB CREDS*'
    PostgresDB.initialize_pool(cnn)

    
