import psycopg2
from psycopg2 import pool
import time
import logging
from contextlib import contextmanager

class PostgresDB:
    connection_pool = None

    def __init__(self, timeout=30, max_retries=5):
        self.timeout = timeout
        self.max_retries = max_retries

    @classmethod
    def create_connection_pool(cls, cnn, minconn=1, maxconn=10):
        attempts = 1
        max_retries = 5
        while attempts <= max_retries:
            try:
                return pool.SimpleConnectionPool(minconn=minconn,
                                                 maxconn=maxconn,
                                                 **cnn)
            except psycopg2.DatabaseError as e:
                print(f'Database error encountered while opening conn pool: {e}')
                #logging.exception(f'Database error encountered: {e}')
                time.sleep(1)
                attempts += 1

    @classmethod
    def initialize_pool(cls, cnn):
        if cls.connection_pool is None:
            cls.connection_pool = cls.create_connection_pool(cnn)

    @classmethod
    def is_pool_ready(cls):
        return cls.connection_pool is not None

    @contextmanager
    def get_connection(self):
        if self.connection_pool is None:
            raise ValueError("Connection pool not initialized")

        conn = self.connection_pool.getconn()
        try:
            print("Acquiring connection pool thread")
            # logging.info("Acquiring connection pool thread")
            yield conn
        finally:
            self.connection_pool.putconn(conn)

    def fetch_proc(self, query, params):
        attempts = 1
        while attempts <= self.max_retries:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (params,))
                    return cursor.fetchall()
            except psycopg2.DatabaseError as e:
                print(f'Database error encountered when fetching data for {query} and {params}: {e}')
                # logging.exception(f'Database error encountered when fetching data for {query} and {params}: {e}')
                attempts+=1
            except Exception as e:
                print(f'Unexpected error encountered when fetching data for {query} and {params}: {e}')
                # logging.exception(f'Database error encountered when fetching data for {query} and {params}: {e}')
                attempts+=1

        return 1 # Learn how to return empty cursor

    def store_proc(self, query, params) -> int:
        attempts = 1

        while attempts <= self.max_retries:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    cursor.execute('COMMIT;')
                    return 0 # success
            except psycopg2.DatabaseError as e:
                print(f'Database error encountered for {query} and {params}: {e}')
                # logging.exception(f'Database error encountered for {query} and {params}: {e}')
                attempts+=1

            except Exception as e:
                print(f'Unexpected error encountered for {query} and {params}: {e}')
                # logging.exception(f'Unexpected error encountered for {query} and {params}: {e}')
                attempts+=1

        return 1 # failure