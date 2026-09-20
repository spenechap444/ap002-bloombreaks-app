import logging

import psycopg2

from application.consumer.core.facade.model.infrastructure.repository.DB import (
    PostgresDB,
    DatabaseOperationError,
)

logger = logging.getLogger(__name__)

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

    # --- Telnyx webhook idempotency -------------------------------------------
    # These two deliberately make ONE attempt and do not go through
    # fetch_proc/store_proc. Those retry with 10s sleeps, which would hold the
    # webhook response past Telnyx's timeout - the exact thing that causes
    # redeliveries. Failing fast is correct here: the handler returns 503 and
    # Telnyx retries the event later on its own schedule.

    def claim_webhook_event(self, event_id, event_type):
        """Record a Telnyx event ID. Returns True if this is the first time we've
        seen it (process it), False if it was already recorded (a redelivery).

        fetch_proc can't be used for this even ignoring the retries: it never
        commits, so the claim row would never become visible to a retry.
        """
        query = 'SELECT records_api_dbo.aip_claim_webhook_event(%s, %s);'
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (event_id, event_type))
                    claimed = cursor.fetchone()[0]
                conn.commit()
            return bool(claimed)
        except psycopg2.Error as e:
            raise DatabaseOperationError(
                f'could not claim webhook event {event_id}') from e

    def release_webhook_event(self, event_id):
        """Undo a claim after processing failed, so Telnyx's retry of the same
        event gets processed instead of skipped. Best effort: a failure here is
        logged, not raised, because the caller is already handling an error.
        """
        query = 'SELECT records_api_dbo.aip_release_webhook_event(%s);'
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (event_id,))
                conn.commit()
        except Exception as e:
            # If this fails, the retry will be treated as a duplicate and the
            # event is lost - log loudly enough to find it in CloudWatch.
            logger.error('Could not release webhook event %s - a Telnyx retry '
                         'of it will be skipped: %s', event_id, e)
