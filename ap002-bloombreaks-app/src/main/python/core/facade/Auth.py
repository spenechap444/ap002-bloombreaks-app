from ..model.AuthModels import users, user_payment_map, user_address_map
from ...infrastructure.repository.AuthDB import authDB
from werkzeug.security import generate_password_hash, check_password_hash
import json
from jsonschema import validate, ValidationError
from types import SimpleNamespace
from Base import BaseService

class AuthService(BaseService):
    def __init__(self, db):
        super().__init__(db)

    def login(self, request):
        db = authDB()
        user = self.login_user_map(request)
        user_cred = db.fetch_user(user.email)
        if user.user_password == user_cred['user_password']:
            return user, None
        elif user.email != user_cred['email']:
            return None, 'Invalid email'
        return None, 'Invalid password'


    # map login request to DB object
    def login_user_map(self, request):
        f_request = self._dict_to_namespace(request)

        user = users(email=f_request.properties.data.email,
                     user_password = f_request.properties.data.userPassword)
        return user
# facade
class AuthServiceV1:
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