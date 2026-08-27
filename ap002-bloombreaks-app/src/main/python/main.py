import logging
import os
import sys

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from application.consumer.core.facade.model.infrastructure.repository.DB import PostgresDB, DatabaseOperationError
from application.consumer.core.facade.model.infrastructure.configuration import initParams as c
from application.consumer.AuthConsumer import auth_bp
from application.consumer.TextConsumer import text_bp


def configure_logging():
    """Route every logger in the app to stdout.

    Called at import time so it runs under gunicorn (which imports wsgi ->
    main) as well as `python main.py`. One handler on the root logger is all
    it takes: module loggers created with logging.getLogger(__name__)
    propagate upward, so they all come out here without any per-module setup.
    stdout (not stderr, not a file) because the container log IS stdout -
    Docker and CloudWatch both collect it.
    """
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
        format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        stream=sys.stdout,
        # force=True clears any handler another library installed first -
        # without it, basicConfig silently does nothing if a handler exists.
        force=True,
    )


configure_logging()
logger = logging.getLogger(__name__)


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
    app.register_blueprint(text_bp)

    @app.route("/ping")
    def ping():
        # This is the load balancer's readiness probe, so it has to answer the
        # question the load balancer is actually asking: can this instance serve
        # a request? A process that is up but cannot reach Postgres cannot, and
        # a bare "pong" would keep it in rotation 500ing every real caller.
        ok, detail = PostgresDB.health_check()

        if ok:
            return jsonify({"status": "ok", "database": "ok"}), 200

        # Log the real reason, return a generic one. /ping is reachable by
        # anything that can reach the load balancer, and psycopg2 error text
        # carries the host, port and database name.
        app.logger.error("Health check failed: %s", detail)

        # 503 (not 500) so the ALB drains this instance and retries it, rather
        # than treating the failure as permanent.
        return jsonify({"status": "error", "database": "unavailable"}), 503

    @app.errorhandler(DatabaseOperationError)
    def handle_db_error(e):
        # A DB failure is the server's problem - report it as one, never as a
        # 200 "success" or a 401 "bad credentials". 503 = try again later.
        logger.error('Database operation failed: %s', e)
        return jsonify({
            "status": "error",
            "message": "Database unavailable - please try again later"
        }), 503

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        # Let real HTTP errors (404, 405, ...) keep their own responses.
        if isinstance(e, HTTPException):
            return e
        # logger.exception attaches the full stack trace to the record, so it
        # reaches stdout -> container log -> CloudWatch with the log format.
        logger.exception('Unhandled exception while serving request')
        # JSON, not Flask's HTML error page - callers do res.json().
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

    return app

# For local testing, we can run the app directly
if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=8000, debug=True)
# http://localhost:8000/auth/login