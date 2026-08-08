from application.consumer.core.facade.model.infrastructure.repository.DB import PostgresDB

class textDB(PostgresDB):
    def __init__(self, timeout=30, max_retries=5):
        super().__init__(timeout, max_retries)

    def fetch_sms_subscribers(self, status_cd='ACTIVE', admin_flag=None):
        # Name the column explicitly - selecting * and taking row[0] would break
        # silently if the proc's return columns are ever reordered, and callers
        # (send_promotion) expect a flat list of phone numbers only.
        query = 'SELECT p_phone_number_o FROM records_api_dbo.fetch_user_messaging_by_status(%s, %s);'

        result = self.fetch_proc(query, (status_cd, admin_flag))
        if isinstance(result, list):
            return [row[0] for row in result]
        return []

    def store_sms_subscriber(self, text_subscriber):
        query = 'CALL records_api_dbo.aip_user_messaging_status_insert(%s, %s, %s, %s);'
        params = (text_subscriber.phone_number,
                  text_subscriber.status_cd,
                  text_subscriber.admin_flag,
                  text_subscriber.create_id)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o
    
    def send_sms_message(self, text_message):
        query = 'CALL account_api_dbo.aip_send_sms_message(%s, %s, %s, %s, %s, %s, %s);'
        params = (text_message.from_number,
                  text_message.to_number,
                  text_message.body,
                  text_message.media_urls,
                  text_message.status,
                  text_message.error_code,
                  text_message.error_message)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o