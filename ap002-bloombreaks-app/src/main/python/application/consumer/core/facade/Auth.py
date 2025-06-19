from application.consumer.core.facade.model.AuthModels import users
from application.consumer.core.facade.model.infrastructure.utils.emailUtil import Email
from werkzeug.security import generate_password_hash, check_password_hash
from application.consumer.core.facade.Base import BaseService
import random

class AuthService(BaseService):
    def __init__(self, db):
        super().__init__(db)
    #fetches user authentication
    def login(self, request):
        f_request = self._dict_to_namespace(request)
        user = users(email=f_request.data.email,
                     user_password = f_request.data.userPassword)

        user_cred = self.db.fetch_user(user.email) # returned as tuple in 1 element list
        user_email = user_cred[3]
        print('user email from DB: ', user_email)
        user_password = generate_password_hash(user_cred[4]) # password is 5th element
        print('user password from DB: ', user_password)
        if user.user_password == user_password:
            print('Password checks out')
            return user, None

        elif user.email != user_email:
            print('Email checks out')
            return None, 'Invalid email'
        print('Nothing checks out')
        return None, 'Invalid password'

    #produces an email
    def send_email_validation(self, init_request, email_cd_mapping):
        f_request = self._dict_to_namespace(init_request)
        security_cd = ''
        for i in range(6):
            security_cd += str(random.randint(0, 9))
        #store security code against email
        email_cd_mapping[f_request.data.email] = security_cd
        email = Email('snchapman4@gmail.com')
        email_body = email.craft_validation_msg(security_cd)
        email.send_mail(p_recip_i=f_request.data.email,
                        p_subject_i='Bloombreaks email validation',
                        p_msgbody_i = email_body)


    def email_validation(self, emailValidateReq, email_cd_mapping):
        f_request = self._dict_to_namespace(emailValidateReq)
        user = users(email=f_request.data.email,
                     user_password=f_request.data.userPassword)
        if f_request.data.securityCode != email_cd_mapping[f_request.data.email]:
            return None, 'Validation failed'
        # store new user in the database
        self.db.store_new_user(user)
        return True, None

    def email_dup_check(self, email_request):
        f_request = self._dict_to_namespace(email_request)
        user = users(email=f_request.data.email)
        print(f'User email checking for duplicate: {user.email}')
        user_cred = self.db.fetch_user(user.email)
        if user_cred is None:
            print('No existing email found.')
            return False, 'No existing email found'
        print(f'Email {user.email} already exists')
        return True, 'Email already existing'

    def rm_security_cd(self, cancel_request, email_cd_mapping):
        f_request = self._dict_to_namespace(cancel_request)
        del email_cd_mapping[f_request.data.email]

    def register(self, registerRequest):
        f_request = self._dict_to_namespace(registerRequest)
        user = users(email=f_request.data.email,
                     user_password = f_request.data.userPassword)

        user.user_password = generate_password_hash(user.user_password)
        return_cd = self.db.store_new_user(user)

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