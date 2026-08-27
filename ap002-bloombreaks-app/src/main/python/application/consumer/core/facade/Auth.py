from application.consumer.core.facade.model.AuthModels import users
from application.consumer.core.facade.model.infrastructure.utils.emailUtil import Email
from werkzeug.security import generate_password_hash, check_password_hash
from application.consumer.core.facade.Base import BaseService
import logging
import random

logger = logging.getLogger(__name__)

class AuthService(BaseService):
    def __init__(self, db):
        super().__init__(db)
    #fetches user authentication

    def login(self, request, admin_check=False):
        f_request = self._dict_to_namespace(request)
        user = users(email=f_request.data.email,
                     user_password = f_request.data.userPassword)

        user_cred = self.db.fetch_user(user.email) # returned as tuple in 1 element list
        if user_cred is None:
            # Unknown email - without this check user_cred[3] raises and the
            # endpoint 500s instead of returning a clean auth failure.
            return None, 'Invalid email'
        user_email = user_cred[3]
        user_password = user_cred[4] # password is 5th element

        # required for any admin functionality
        if admin_check:
            admin_flag = user_cred[10]
            if admin_flag != 'Y':
                logger.info('Admin login rejected for %s - not an admin', user_email)
                return None, 'User is not an admin'
            else:
                logger.info('Admin login accepted for %s', user_email)

        if check_password_hash(user_password, user.user_password):
            logger.debug('Password check passed')
            return user, None

        elif user.email != user_email:
            logger.debug('Email matched but password did not')
            return None, 'Invalid email'
        logger.debug('Neither email nor password matched')
        return None, 'Invalid password'

    #produces an email
    def send_email_validation(self, init_request, email_cd_mapping):
        f_request = self._dict_to_namespace(init_request)
        security_cd = ''
        for i in range(6):
            security_cd += str(random.randint(0, 9))
        #store security code against email
        email_cd_mapping[f_request.data.email] = security_cd
        email = Email('BloomsHobbyShop@gmail.com')
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
        logger.debug('Checking for duplicate email: %s', user.email)
        user_cred = self.db.fetch_user(user.email)
        if user_cred is None:
            logger.debug('No existing email found')
            return False, 'No existing email found'
        logger.info('Registration attempted with existing email: %s', user.email)
        return True, 'Email already existing'

    def rm_security_cd(self, cancel_request, email_cd_mapping):
        f_request = self._dict_to_namespace(cancel_request)
        del email_cd_mapping[f_request.data.email]

    def register(self, registerRequest):
        f_request = self._dict_to_namespace(registerRequest)
        user = users(email=f_request.data.email,
                     user_password = f_request.data.userPassword)

        user.user_password = generate_password_hash(user.user_password)
        user.account_id = generate_password_hash(user.email)
        return_cd = self.db.store_new_user(user)
        return return_cd
    
    def update_user_info(self, updateRequest):
        f_request = self._dict_to_namespace(updateRequest)
        user = users(email=f_request.data.email,
                     first_name=f_request.data.firstName,
                     last_name=f_request.data.lastName,
                     user_name=f_request.data.userName,
                     bio=f_request.data.bio,
                     notifications=f_request.data.notifications,
                     phone_nbr=f_request.data.phoneNbr)
        return_cd = self.db.update_user_info(user)
        return return_cd