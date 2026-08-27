from flask import Blueprint, render_template, request, jsonify
from jsonschema import validate, ValidationError
from application.consumer.core.facade.Auth import AuthService
from application.consumer.core.facade.model.infrastructure.repository.AuthDB import authDB
import logging
import os
import json

logger = logging.getLogger(__name__)

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
        validate(instance=payload, schema=contract_template.get('loginRequest'))
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    # Process registration with AuthService
    db = authDB()
    auth = AuthService(db)

    auth.register(payload)

    return jsonify({
        "status": "success",
        "message": "account created successfully"
    }), 200


#TODO: remove this endpoint and move the logic to register endpoint
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
        validate(instance=payload, schema=contract_template['loginRequest'])
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    # service level implementation for checking email
    found_flag, msg = auth.email_dup_check(payload)

    if found_flag:
        return jsonify({
            "status": "failure",
            "flag": found_flag,
            "message": msg
        }), 400
    else:
        # creating the account
        auth.register(payload)
        return jsonify({
            "status": "success",
            "flag": found_flag,
            "message": msg
        }), 200

#TODO: remove this endpoint and move the logic to register endpoint
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
        logger.debug('Login request validated successfully')
    except ValidationError as ve:
        return jsonify({"status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    user, err_msg = auth.login(payload)

    # Never echo credentials back to the caller (or into logs) - the client
    # already knows what it submitted; it only needs to know whether it worked.
    if user is not None:
        return jsonify({
            "status": "success",
            "message": "Login successful"
        }), 200
    else:
        # Deliberately generic: don't reveal whether the email or the password
        # was wrong, and use 401 (unauthorized) rather than 400 (bad request).
        return jsonify({
            "status": "error",
            "message": "Invalid credentials"
        }), 401
    
@auth_bp.route('/update_user_info', methods=['POST'])
def update_user_info():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    # Validate the payload against the template
    try:
        validate(instance=payload, schema=contract_template['updateUserInfoRequest'])
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    db = authDB()
    auth = AuthService(db)
    p_return_cd_o = auth.update_user_info(payload)

    if p_return_cd_o == 0:
        return jsonify({
            "status": "success",
            "message": "User info updated successfully"
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": f"Failed to update user info, return code: {p_return_cd_o}"
        }), 500