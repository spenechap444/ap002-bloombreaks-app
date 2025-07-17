from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'CARD_PRODUCT'
    __schemaname__ = 'PRODUCT_DBO'
    product_id = db.Column(db.String(300), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    product_category = db.Column(db.String(100), nullable=False)
    game_or_sport = db.Column(db.String(10))
    set_name = db.Column(db.String(50))
    release_date = db.Column(db.Date)
    product_type = db.Column(db.String(50))
    pack_count = db.Column(db.Integer)
    card_count_per_pack = db.Column(db.Integer)
    total_card_count = db.Column(db.Integer)
    promo_included = db.Column(db.Boolean)
    promo_details = db.Column(db.String(300))
    msrp = db.Column(Numeric(10, 2), nullable=False)
    cost_price = db.Column(Numeric(10, 2), nullable=False)
    sale_price = db.Column(Numeric(10, 2))
    sku = db.Column(db.String(100))
    barcode = db.Column(db.String(300))
    inventory_count = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(300))
    description = db.Column(db.String(300))
    sealed = db.Column(db.Boolean)
    is_active = db.Column(db.Boolean, nullable=False)

class SportCard(db.Model):
    __tablename__ = 'SPORTS_CARDS'
    __schemaname__ = 'PRODUCT_DBO'
    card_id = db.Column(db.String(300), nullable=False)
    player_name = db.Column(db.String(60), nullable=False)
    rookie = db.Column(db.Boolean, nullable=False)
    autograph_cd = db.Column(db.String(15))
    patch = db.Column(db.String(30))
    path_color_cnt = db.Column(db.Integer)
    team = db.Column(db.String(60), nullable=False)
    numbered = db.Column(db.String(15))
    sport_type_cd = db.Column(db.String(30), nullable=False)
    product_cd = db.Column(db.String(30))
    img_link = db.Column(db.String(300))
    variant = db.Column(db.Boolean)
    grade_type = db.Column(db.String(30), nullable=False)
    grade_score = db.Column(Numeric(2,1))
    msrp = db.Column(Numeric(10, 2))
    cost_price = db.Column(Numeric(10, 2))
    sale_price = db.Column(Numeric(10, 2))




