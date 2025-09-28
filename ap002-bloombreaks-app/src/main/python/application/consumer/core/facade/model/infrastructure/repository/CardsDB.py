from application.consumer.core.facade.model.infrastructure.repository.DB import PostgresDB

class cardsDB(PostgresDB):
    def __init__(self, timeout=30, max_retries=5):
        super().__init__(timeout, max_retries)

    def fetch_sports_cards(self, sportCardInput):
        query = "SELECT * FROM PRODUCT_API_DBO.AIP_FETCH_SPORTS_CARDS(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
        params = (sportCardInput.rookie_flag,
                  sportCardInput.auto_flag,
                  sportCardInput.patch_flag,
                  sportCardInput.team_name,
                  sportCardInput.numbered_flag,
                  sportCardInput.sport_card_type_cd,
                  sportCardInput.product_cd,
                  sportCardInput.variant_flag,
                  sportCardInput.grade_cd,
                  sportCardInput.grade_score,
                  sportCardInput.min_price,
                  sportCardInput.max_price,
                  sportCardInput.limit,
                  sportCardInput.offset)

        sports_cards = self.fetch_proc(query, params)
        return sports_cards