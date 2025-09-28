import stripe
import os
from Base import BaseService

# should be in startup logic not in class declaration
stripe.api_key = os.environ['STRIPE_API_KEY']

class PaymentService(BaseService):
    def __init__(self, db):
        super().__init__(db)

    def make_payment(self, payment_request):
        payment = self._dict_to_namespace(payment_request)
        user_payment = self.db.fetch_user_payment_map(payment.data.email) # db implementation for fetching payment info

        itent = stripe.PaymentIntent.create(
            amount=user_payment.data.amount,
            currency=user_payment.data.currency,
            customer=user_payment.data.customer_id,
            confirm=True
        )