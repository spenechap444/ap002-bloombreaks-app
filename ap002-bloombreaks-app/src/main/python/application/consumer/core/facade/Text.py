import telnyx
import os
from application.consumer.core.facade.Base import BaseService

# should be in startup logic not in class declaration
telnyx.api_key = os.environ['TELNYX_API_KEY']

class TextService(BaseService):
    def __init__(self, db):
        super().__init__(db)
        self.from_number = os.environ['TELNYX_PHONE_NUMBER']

    def subscribe(self, subscribe_request):
        f_request = self._dict_to_namespace(subscribe_request)
        phone_number = f_request.data.phoneNumber
        success, msg = self.db.store_sms_subscriber(phone_number)
        return success, msg

    def unsubscribe(self, unsubscribe_request):
        f_request = self._dict_to_namespace(unsubscribe_request)
        phone_number = f_request.data.phoneNumber
        success, msg = self.db.remove_sms_subscriber(phone_number)
        return success, msg

    def send_promotion(self, promotion_request):
        f_request = self._dict_to_namespace(promotion_request)
        subscribers = self.db.fetch_sms_subscribers()
        failed = []
        for number in subscribers:
            try:
                telnyx.Message.create(
                    from_=self.from_number,
                    to=number,
                    text=f_request.data.message
                )
            except telnyx.error.TelnyxError as e:
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
        else:
            print(f'Unhandled Telnyx event type: {event_type}')

    def _handle_inbound(self, f_payload):
        # Handle opt-out replies (STOP) from subscribers
        from_number = f_payload.data.payload.from_.phone_number
        message_body = f_payload.data.payload.text.strip().upper()
        print(f'Inbound SMS from {from_number}: {message_body}')

        if message_body == 'STOP':
            self.db.remove_sms_subscriber(from_number)
            print(f'Unsubscribed {from_number} via STOP reply')
