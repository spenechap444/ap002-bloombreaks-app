from application.consumer.core.facade.model.infrastructure.utils.emailUtil import Email
from application.consumer.core.facade.Base import BaseService

class SportsCardsService(BaseService):
    def __init__(self, db):
        super().__init__(db)

    def fetch_category_filtered(self, fetch_card_request):
        pass

    def store_single_card(self, store_card_request):
        pass

    def store_bulk_cards(self, store_bulk_request):
        pass

class CardProductService(BaseService):
    def __init__(self, db):
        super().__init__(db)

    def fetch_product_filtered(self):
        pass

    def store_product(self, store_product_request):
        pass