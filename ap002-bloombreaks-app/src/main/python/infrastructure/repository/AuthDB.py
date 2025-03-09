from DB import PostgresDB

class authDB(PostgresDB):
    def __init__(self, timeout=30, max_retries=5):
        super().__init__(timeout, max_retries)

    def fetch_user(self, p_email_i):
        query = 'SELECT * FROM account_api_dbo.aip_fetch_user(%s);'

        p_cur_o = self.fetch_proc(query, p_email_i,)
        return p_cur_o.fetchone() # first row as dict obj

    def insert_user_account_payment(self, user_pmt_type):
        query = 'CALL account_api_dbo.aip_add_user_payment(%s, %s, %s, %s, %s, %s, %s, %s);'
        params = (user_pmt_type.account_id,
                  user_pmt_type.card_id,
                  user_pmt_type.card_nbr,
                  user_pmt_type.card_name,
                  user_pmt_type.card_provider,
                  user_pmt_type.security_cd,
                  user_pmt_type.exp_date,
                  user_pmt_type.active_ind)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o

    def update_active_payment(self, account_id, card_id):
        query = 'CALL account_api_dbo.aip_update_active_payment'
        params = (account_id, card_id)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o

    def update_user_info(self, user_type): # omitting email from update
        query = 'CALL account_api_dbo.aip_update_user_info(%s, %s, %s, %s, %s, %s);'
        params = (user_type.account_id,
                  user_type.first_name,
                  user_type.last_name,
                  user_type.user_name,
                  user_type.bio,
                  user_type.notifications)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o

    def store_new_user(self, user_type):
        query = 'CALL account_api_dbo.aip_store_new_user(%s, %s, %s, %s, %s, %s, %s, %s);'
        params = (user_type.first_name,
                  user_type.last_name,
                  user_type.user_name,
                  user_type.email,
                  user_type.user_passwword,
                  user_type.bio,
                  user_type.account_id,
                  user_type.notifications)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o

    def upsert_user_address(self, user_addr_type):
        query = 'CALL account_api_dbo.aip_upsert_user_address(%s, %s, %s, %s, %s, %s, %s);'
        params = (user_addr_type.account_id,
                  user_addr_type.user_address,
                  user_addr_type.city,
                  user_addr_type.state_cd,
                  user_addr_type.zip_cd,
                  user_addr_type.country,
                  user_addr_type.active_ind)

        p_return_cd_o = self.store_proc(query, params)

        return p_return_cd_o