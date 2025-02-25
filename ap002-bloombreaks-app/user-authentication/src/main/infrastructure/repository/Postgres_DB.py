import psycopg2
from psycopg2 import pool
import time
import logging

class Postgres:
    def __init__(self, cnn):
        self.__cnn = cnn # json object w/ cnn details
        self.max_retries = 5
        self.delay = 1

    def open_pool(self, minconn=1, maxconn=10):
        attempts = 1
        while attempts <= self.max_retries:
            try:
                 pool.SimpleConnectionPool(minconn=minconn,
                                                 maxconn=maxconn,
                                                 **self.__cnn)
            except psycopg2.DatabaseError as e:
                print(f'Database error encountered: {e}')
                #logging.exception(f'Database error encountered: {e}')
                time.sleep(self.delay)
                attempts += 1
            except Exception as e:
                print(f'Unexpected error encountered: {e}')
                logging.exception(f'Unexpected error encountered: {e}')