from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric

db = SQLAlchemy()

class transactions(db.Model):
    __tablename__ = 'TRANSACTIONS'
    __schemaname__ = 'RECORDS_DBO'
    transaction_id = db.Column(db.String(300), nullable=False, primary_key=True)
    shipment_id = db.Column(db.String(300), nullable=False)
    transaction_ts = db.Column(db.DateTime)
    card_id = db.Column(db.String(300))
    product_id = db.Column(db.String(300))
    transaction_amt = db.Column(Numeric(precision=10, scale=2))
    account_id = db.Column(db.String(300), nullable=False)
    currency_cd = db.Column(db.String(4), nullable=False)