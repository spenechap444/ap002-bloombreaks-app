from flask import Blueprint, render_template, request, jsonify
from jsonschema import validate, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from ...core.facade.Auth import AuthService
from ...infrastructure.repository.AuthDB import authDB
import os

# Create a blueprint for authentication-related routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
contract_template = open(os.path.join(os.path.dirname(__file__), 'templates/authContracts.json'))

@auth_bp.route('/register', methods=['POST'])
def validate_email():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    # Validate the payload against the template
    try:
        validate(instance=payload, schema = contract_template['login'])
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    user, err_msg = auth.login(payload)
    return jsonify({
        "status": "success",
        "data": payload,
        "message": "User registration validated and processed"
    }), 200

@auth_bp.route('/login', methods=['POST'])
def fetch_auth():
    payload = request.get_json()

    try:
        validate(instance=payload)
    except ValidationError as ve:
        return jsonify({"status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    user, err_msg = auth.login(payload)
    if user is not None:
        return jsonify({
            "email": user.email,
            "userPassword": user.userPassword
        })

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Process login logic here
        return jsonify({'message': 'Logged in successfully'})
    return render_template('login.html')

@auth_bp.route('/register', methods=['POST'])
def register():
    # Process registration logic here
    return jsonify({'message': 'User registered successfully'})