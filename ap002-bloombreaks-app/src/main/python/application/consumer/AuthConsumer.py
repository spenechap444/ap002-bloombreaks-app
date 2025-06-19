from flask import Blueprint, render_template, request, jsonify
from jsonschema import validate, ValidationError
from application.consumer.core.facade.Auth import AuthService
from application.consumer.core.facade.model.infrastructure.repository.AuthDB import authDB
import os
import json

# Create a blueprint for authentication-related routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
contract_template = open(os.path.join(os.path.dirname(__file__), 'templates/authContracts.json'))
with open(os.path.join(os.path.dirname(__file__), 'templates/authContracts.json')) as f:
    contract_template = json.load(f)

@auth_bp.route('/register', methods=['POST'])
def register():

    # validation logic (modularize with decorator
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    # Validate against the 'register' contract
    try:
        validate(instance=payload, schema=contract_template.get('register'))
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    # Process registration with AuthService
    db = authDB()
    auth = AuthService(db)

@auth_bp.route('/emailDupCheck', methods=['POST'])
def emailDupCheck():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    # Validate the payload against the template
    try:
        validate(instance=payload, schema=contract_template['emailDupCheck'])
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    # service level implementation for checking email
    found_flag, msg = auth.emailDupCheck(payload)

    return jsonify({
        "status": "success",
        "flag": found_flag,
        "message": msg
    }), 200

@auth_bp.route('/email_validate', methods=['POST'])
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

    # found_flag, msg = auth.emailDupCheck(payload)
    #
    #
    # return jsonify({
    #     "status": "success",
    #     "flag": found_flag,
    #     "message": msg
    # }), 200

@auth_bp.route('/login', methods=['POST'])
def fetch_auth():
    payload = request.get_json()

    try:
        validate(instance=payload, schema=contract_template.get('loginRequest'))
        print('Login request validated successfully..')
    except ValidationError as ve:
        return jsonify({"status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    user, err_msg = auth.login(payload)
    print('User:', user)
    print('err_msg:', err_msg)


    # Need to modify this to a uniform contract for the caller
    if user is not None:
        return jsonify({
            "email": user.email,
            "userPassword": user.user_password
        }), 200
    else:
        return jsonify({"status": "error",
                        "message": "Login information not found",
                        "error": None
                    }), 400