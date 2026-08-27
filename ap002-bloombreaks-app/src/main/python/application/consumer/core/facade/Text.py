import telnyx
import logging
import os
import base64
import time
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from application.consumer.core.facade.Base import BaseService
from application.consumer.core.facade.model.TextModels import text_subscribers

logger = logging.getLogger(__name__)

# should be in startup logic not in class declaration
telnyx.api_key = os.environ['TELNYX_API_KEY']

class TextService(BaseService):
    def __init__(self, db):
        super().__init__(db)
        self.from_number = os.environ['TELNYX_PHONE_NUMBER']
        self.public_key = os.environ['TELNYX_PUBLIC_KEY']

    def verify_webhook_signature(self, raw_body, signature_header, timestamp_header, tolerance_seconds=300):
        # Confirms a webhook actually came from Telnyx (Ed25519), not a forged
        # request hitting our public endpoint. Must run BEFORE we trust the payload.
        if not signature_header or not timestamp_header:
            logger.warning('Telnyx webhook rejected: missing signature headers')
            return False

        try:
            if abs(time.time() - int(timestamp_header)) > tolerance_seconds:
                logger.warning('Telnyx webhook rejected: timestamp outside tolerance window')
                return False

            verify_key = VerifyKey(base64.b64decode(self.public_key))
            # Telnyx signs the string "{timestamp}|{raw_json_body}" - this MUST be
            # checked against the raw bytes Telnyx sent, not a re-serialized dict,
            # or verification will fail even for a legitimate webhook.
            signed_payload = f'{timestamp_header}|{raw_body.decode("utf-8")}'.encode('utf-8')
            verify_key.verify(signed_payload, base64.b64decode(signature_header))
            return True
        except (BadSignatureError, ValueError, TypeError) as e:
            logger.warning('Telnyx webhook signature verification failed: %s', e)
            return False

    def subscribe(self, phone_number):
        text_subscriber = text_subscribers(phone_number=phone_number,
                                            status_cd='ACTIVE',
                                            create_id='TELNYX_WEBHOOK',
                                            create_ts=self._get_current_timestamp())
        return_cd = self.db.store_sms_subscriber(text_subscriber)

        if return_cd == 0:
            return True, 'Subscribed successfully'
        return False, 'Failed to subscribe'

    def unsubscribe(self, phone_number):
        text_subscriber = text_subscribers(phone_number=phone_number,
                                            status_cd='INACTIVE',
                                            create_id='TELNYX_WEBHOOK',
                                            create_ts=self._get_current_timestamp())
        return_cd = self.db.store_sms_subscriber(text_subscriber)

        if return_cd == 0:
            return True, 'Unsubscribed successfully'
        return False, 'Failed to unsubscribe'

    def send_promotion(self, promotion_request):
        f_request = self._dict_to_namespace(promotion_request)
        subscribers = self.db.fetch_sms_subscribers()
        # Zero subscribers is the silent-failure trap: without this log an empty
        # fetch (no active rows, or a NULL admin_flag filtering everything out)
        # looks identical to a real send.
        logger.info('Fetched %d active subscriber(s) for promotion', len(subscribers))
        if not subscribers:
            return False, 'No active subscribers found - nothing sent'
        failed = []
        for number in subscribers:
            try:
                logger.info('Sending promotion to %s', number)
                logger.debug('Promotion body: %s', f_request.data.message)
                client = telnyx.Telnyx(api_key=telnyx.api_key)
                response = client.messages.send(
                    from_=self.from_number,
                    to=number,
                    text=f_request.data.message
                )
            except Exception as e:
                logger.error('Telnyx error sending to %s: %s', number, e)
                failed.append(number)

        if failed:
            return False, f'Promotion sent with {len(failed)} failure(s)'
        return True, 'Promotion sent successfully'

    def handle_webhook(self, webhook_payload):
        f_payload = self._dict_to_namespace(webhook_payload)
        event_type = f_payload.data.event_type

        if event_type == 'message.received':
            self._handle_inbound(f_payload)
        elif event_type in ('message.sent', 'message.finalized'):
            # Delivery-status events. 'to[].status' is the carrier's verdict
            # (delivered / sending / delivery_failed); 'errors' has the reason codes.
            raw = webhook_payload['data']['payload']
            for recipient in raw.get('to', []):
                logger.info('%s: to=%s status=%s', event_type,
                            recipient.get('phone_number'), recipient.get('status'))
            if raw.get('errors'):
                logger.error('%s errors: %s', event_type, raw['errors'])
        else:
            logger.info('Unhandled Telnyx event type: %s', event_type)

    def _handle_inbound(self, f_payload):
        # Telnyx only ever hits this one webhook endpoint, so all keyword-based
        # opt-in/opt-out dispatch lives here rather than as separate routes.
        # Telnyx's payload key is literally "from", which is a reserved word
        # in Python, so dot-notation (.from_) can't reach it - getattr is required.
        from_number = getattr(f_payload.data.payload, 'from').phone_number
        raw_text = f_payload.data.payload.text.strip()
        message_body = raw_text.upper()
        logger.info('Inbound SMS from %s: %s', from_number, message_body)

        if message_body == 'YES':
            success, msg = self.subscribe(from_number)
            logger.info('Subscribe result for %s: %s - %s', from_number, success, msg)
        elif message_body == 'STOP':
            success, msg = self.unsubscribe(from_number)
            logger.info('Unsubscribe result for %s: %s - %s', from_number, success, msg)
        elif message_body.startswith('PROMO'):
            # Pass raw_text, not the uppercased copy - the promotion message
            # should go out with its original casing.
            self._handle_admin_promo(from_number, raw_text)
        else:
            logger.info('No matching keyword for %r from %s - ignoring', message_body, from_number)

    # TODO: This can be deleted if promotion feature is built and this is forgotten
    # def _validate_admin(self, payload):
    #     # Admin-only: authenticate a promotion request by checking the email
    #     # admin flag and password in the DB. This is a separate auth path from the Telnyx webhook signature.
    #     f_payload = self._dict_to_namespace(payload)
    #     email = f_payload.data.email
    #     user_password = f_payload.data.userPassword

    #     # user_cred = self.db.fetch_user(email)
    #     admin_flag = self.db.fetch_sms_subscribers(admin_flag='Y')
    #     if not admin_flag:
    #         print(f'Admin promo rejected, user is not stored as admin')


    #     if not user_cred or user_cred.password != user_password:
    #         print(f'Admin promo rejected: invalid credentials for {email}')
    #         return False
        


    def _handle_admin_promo(self, from_number, raw_text):
        # Admin-only: broadcast a promotion by texting "PROMO <pin> <message>"
        # to our Telnyx number. Three auth layers, checked in order:
        #   1. Webhook Ed25519 signature (already verified upstream) - proves the
        #      event really came through Telnyx, so it can't be forged via curl.
        #   2. Sender allowlist - only numbers in ADMIN_PHONE_NUMBERS may trigger.
        #   3. Shared PIN in the message body - guards against SMS sender spoofing.
        admins = self.db.fetch_sms_subscribers(admin_flag='Y')

        # Check if the sender is in the admin list
        is_admin = False
        for number in admins:
            is_admin = True if number == from_number else is_admin

        if not is_admin:
            logger.warning('PROMO rejected: %s is not an admin', from_number)
            return
        pin = os.environ.get('ADMIN_SMS_PIN')
        parts = raw_text.split(maxsplit=2)  # ["PROMO", "<pin>", "<message>"]
        if not pin:
            logger.error('PROMO rejected: ADMIN_SMS_PIN is not configured')
            return
        if len(parts) < 3 or parts[1] != pin:
            logger.warning('PROMO rejected: bad or missing PIN from %s', from_number)
            return

        success, msg = self.send_promotion({'data': {'message': parts[2]}})
        logger.info('Admin promo from %s: %s - %s', from_number, success, msg)
