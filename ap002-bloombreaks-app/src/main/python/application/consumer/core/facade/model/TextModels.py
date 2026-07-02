from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric

db = SQLAlchemy()

class text_subscribers(db.Model):
    __tablename__ = 'USER_MESSAGING_STATUS'
    __schemaname__ = 'RECORDS_DBO'
    phone_number = db.Column(db.String(20), nullable=False, primary_key=True)
    status_cd = db.Column(db.String(10), nullable=False)  # ACTIVE, INACTIVE
    create_id = db.Column(db.String(30), nullable=False)
    create_ts = db.Column(db.DateTime, nullable=False)
    update_id = db.Column(db.String(30))
    update_ts = db.Column(db.DateTime)

class text_message(db.Model):
    __tablename__ = 'MESSAGE_TRACKER'
    __schemaname__ = 'RECORDS_DBO'
    id = db.Column(db.String(300), primary_key=True)
    telnyx_message_id = db.Column(db.String(300))
    messaging_profile_id = db.Column(db.String(300))
    from_number = db.Column(db.String(20), nullable=False)
    to_number = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'inbound' or 'outbound'
    body = db.Column(db.Text)
    media_urls = db.Column(db.ARRAY(db.Text))
    status = db.Column(db.String(50))  # queued, sent, delivered, failed
    error_code = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    webhook_received_ts = db.Column(db.DateTime)  # when the flask app received the webhook
    carrier = db.Column(db.String(100))
    sent_ts = db.Column(db.DateTime)  # when telnyx sent/received it
    delivered_ts = db.Column(db.DateTime)
    create_ts = db.Column(db.DateTime)
    update_ts = db.Column(db.DateTime)