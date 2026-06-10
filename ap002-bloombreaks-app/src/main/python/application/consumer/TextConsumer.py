from flask import Blueprint, request, jsonify
from application.consumer.core.facade.Text import TextService
from application.consumer.core.facade.model.infrastructure.repository.TextDB import textDB

# Create a blueprint for text/SMS-related routes
text_bp = Blueprint('text', __name__, url_prefix='/text')

@text_bp.route('/subscribe', methods=['POST'])
def subscribe():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    db = textDB()
    text = TextService(db)
    success, msg = text.subscribe(payload)

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

@text_bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

    db = textDB()
    text = TextService(db)
    success, msg = text.unsubscribe(payload)

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

@text_bp.route('/promotion', methods=['POST'])
def send_promotion():
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing JSON payload"
        }), 400

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
    payload = request.get_json()
    if not payload:
        return jsonify({
            "status": "error",
            "message": "Missing webhook payload"
        }), 400

    db = textDB()
    text = TextService(db)
    text.handle_webhook(payload)

    return jsonify({
        "status": "success"
    }), 200