from flask import Blueprint, request, jsonify
from jsonschema import validate, ValidationError
from application.consumer.core.facade.Text import TextService
from application.consumer.core.facade.model.infrastructure.repository.TextDB import textDB
from application.consumer.core.facade.Auth import AuthService
from application.consumer.core.facade.model.infrastructure.repository.AuthDB import authDB
import os
import json

# Create a blueprint for text/SMS-related routes
text_bp = Blueprint('text', __name__, url_prefix='/text')
with open(os.path.join(os.path.dirname(__file__), 'templates/textContracts.json')) as f:
    contract_template = json.load(f)

@text_bp.route('/promotion', methods=['POST'])
def send_promotion():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    # Validate against the 'promotionRequest' contract - data.email/data.userPassword
    # are required so the producer app can authenticate the same way a logged-in
    # user does, via AuthService.login(), instead of a separate shared API key.
    try:
        validate(instance=payload, schema=contract_template.get('promotionRequest'))
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    auth_db = authDB()
    auth = AuthService(auth_db)
    user, err_msg = auth.login(payload)
    if user is None:
        return jsonify({
            "status": "error",
            "message": err_msg or "Unauthorized"
        }), 401

    db = textDB()
    text = TextService(db)
    success, msg = text.send_promotion(payload)

    if success:
        return jsonify({
            "status": "success",
            "message": msg
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": msg
        }), 400

@text_bp.route('/webhook', methods=['POST'])
def telnyx_webhook():
    # Grab the raw bytes BEFORE touching get_json() - signature verification has
    # to run against exactly what Telnyx sent over the wire, not a re-serialized dict.
    raw_body = request.get_data()
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing webhook payload"
        }), 400

    db = textDB()
    text = TextService(db)

    signature_header = request.headers.get('telnyx-signature-ed25519')
    timestamp_header = request.headers.get('telnyx-timestamp')
    if not text.verify_webhook_signature(raw_body, signature_header, timestamp_header):
        return jsonify({
            "status": "error",
            "message": "Invalid webhook signature"
        }), 401

    # Validate against Telnyx's documented webhook envelope (not our contract -
    # this shape is dictated by Telnyx). Kept loose on payload internals since
    # Telnyx can add fields without notice.
    try:
        validate(instance=payload, schema=contract_template.get('telnyxWebhookEnvelope'))
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON format",
            "error": str(ve)
        }), 400

    text.handle_webhook(payload)

    return jsonify({
        "status": "success"
    }), 200
