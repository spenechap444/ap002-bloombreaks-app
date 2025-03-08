from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class users(db.Model):
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    user_name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    user_password = db.Column(db.String(64), nullable=False)
    bio = db.Column(db.String(300))
    account_id = db.Column(db.String(64), primary_key=True)

class user_payment_map(db.Model):
    account_id = db.Column(db.String(64), primary_key=True)
    card_id = db.Column(db.String(64), primary_key=True)
    card_nbr = db.Column(db.String(15), nullable=False)
    card_name = db.Column(db.String(50), nullable=False)
    card_provider = db.Column(db.String(30), nullable=False)
    security_cd = db.Column(db.Integer, nullable=False)
    exp_date = db.Column(db.Date, nullable=False) # double check on this
    active_ind = db.Column(db.Boolean, nullable=False) # double check on this

class user_address_map(db.Model):
    account_id = db.Column(db.String(64), primary_key=True)
    user_address = db.Column(db.String(300), primary_key=True)
    city = db.Column(db.String(50), nullable = False)
    state_cd = db.Column(db.String(2), nullable=False)
    zip_cd = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(30), nullable=False)
    active_ind = db.Column(db.Boolean, nullable=False)