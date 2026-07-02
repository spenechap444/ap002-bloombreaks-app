import telnyx
import os
import base64
import time
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from application.consumer.core.facade.Base import BaseService
from application.consumer.core.facade.model.TextModels import text_subscribers

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
            print('Telnyx webhook rejected: missing signature headers')
            return False

        try:
            if abs(time.time() - int(timestamp_header)) > tolerance_seconds:
                print('Telnyx webhook rejected: timestamp outside tolerance window')
                return False

            verify_key = VerifyKey(base64.b64decode(self.public_key))
            # Telnyx signs the string "{timestamp}|{raw_json_body}" - this MUST be
            # checked against the raw bytes Telnyx sent, not a re-serialized dict,
            # or verification will fail even for a legitimate webhook.
            signed_payload = f'{timestamp_header}|{raw_body.decode("utf-8")}'.encode('utf-8')
            verify_key.verify(signed_payload, base64.b64decode(signature_header))
            return True
        except (BadSignatureError, ValueError, TypeError) as e:
            print(f'Telnyx webhook signature verification failed: {e}')
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
        failed = []
        for number in subscribers:
            try:
                print(f'Sending promotion to {number}: {f_request.data.message}')
                client = telnyx.Telnyx(api_key=telnyx.api_key)
                response = client.messages.send(
                    from_=self.from_number,
                    to=number,
                    text=f_request.data.message
                )
            except Exception as e:
                print(f'Telnyx error sending to {number}: {e}')
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
                print(f"{event_type}: to={recipient.get('phone_number')} "
                      f"status={recipient.get('status')}")
            if raw.get('errors'):
                print(f'{event_type} errors: {raw["errors"]}')
        else:
            print(f'Unhandled Telnyx event type: {event_type}')

    def _handle_inbound(self, f_payload):
        # Telnyx only ever hits this one webhook endpoint, so all keyword-based
        # opt-in/opt-out dispatch lives here rather than as separate routes.
        # Telnyx's payload key is literally "from", which is a reserved word
        # in Python, so dot-notation (.from_) can't reach it - getattr is required.
        from_number = getattr(f_payload.data.payload, 'from').phone_number
        message_body = f_payload.data.payload.text.strip().upper()
        print(f'Inbound SMS from {from_number}: {message_body}')

        if message_body == 'YES':
            success, msg = self.subscribe(from_number)
            print(f'Subscribe result for {from_number}: {success} - {msg}')
        elif message_body == 'STOP':
            success, msg = self.unsubscribe(from_number)
            print(f'Unsubscribe result for {from_number}: {success} - {msg}')
        else:
            print(f'No matching keyword for "{message_body}" from {from_number} - ignoring')
