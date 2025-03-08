from .core.model import AuthModels
from src.main.python.core.model.AuthModels import user, user_payment_map, user_address_map
from ..model.AuthModels import users, user_payment_map, user_address_map

class AuthService:
    def __init__(self, db):
        self.db = db

    def login(self, users):
        # map the json contract to the users object


# facade
class AuthService:
    def __init__(self, db):
        self.db = db

    def register(self, username, password):
        if User.query.filter_by(username=username).first():
            return None, "User already exists."

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)

        self.db.session.add(new_user)
        self.db.session.commit()
        return new_user, None

    def login(self, username, password):
        user = User.query.filter_by(username).first()  # replace with fetch procedure
        if not user or not check_password_hash(user.password_hash, password):
            return None, "Invalid username or password"
        return user, None