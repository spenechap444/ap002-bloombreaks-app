from flask import Flask
from application.consumer.core.facade.model.infrastructure.repository.DB import PostgresDB
from application.consumer.core.facade.model.infrastructure.configuration import initParams as c
from application.consumer.AuthConsumer import auth_bp


# function for creating database credential mappings
# def parse_creds():
#     # initialize Argument Parser
#     parser = argparse.ArgumentParser(
#         description='Performing validation on API spin up'
#     )
#
#     parser.add_argument('--username', type=str, help='Database username')
#     parser.add_argument('--db_password', type=str, help='Database password')
#     args = parser.parse_args()
#
#     with open(os.path.join(os.path.dirname(__file__), 'infrastructure/configuration/config.json'), 'r') as f:
#         db_creds = json.load(f)
#         db_creds['username'] = args.username
#         db_creds['password'] = args.db_password
#
#     return db_creds
    # parser.add_argument('--stripe_api_key', type=str, help='API key for Sripe transactions')
def create_app(config_name='development'):
    app = Flask(__name__)

    # Load appropriate configuration
    if config_name == 'production':
        config = c.ProductionConfig()
    else:
        config = c.DevelopmentConfig()


    cnn = config.db_creds
    PostgresDB.initialize_pool(cnn)

    app.register_blueprint(auth_bp)

    @app.route("/ping")
    def ping():
        return "pong", 200

    return app

# For local testing, we can run the app directly
if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=8000, debug=True)