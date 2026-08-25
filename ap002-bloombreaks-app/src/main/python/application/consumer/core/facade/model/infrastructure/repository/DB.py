import psycopg2
from psycopg2 import pool
import os
import time
import logging
from contextlib import contextmanager


class DatabaseOperationError(Exception):
    """Raised when a query still fails after every retry.

    Flask turns this into a 503 via the errorhandler in main.py, so a
    database failure can never masquerade as a 200/401/"no rows" response.
    """


class PostgresDB:
    connection_pool = None
    # Pid that built the pool + the creds used, so a forked child (e.g. under
    # gunicorn --preload) can detect the stale pool and rebuild its own.
    _pool_pid = None
    _pool_creds = None

    def __init__(self, timeout=30, max_retries=5):
        self.timeout = timeout
        self.max_retries = max_retries

    @classmethod
    def create_connection_pool(cls, cnn, minconn=1, maxconn=10):
        attempts = 1
        max_retries = 10
        last_error = None
        while attempts <= max_retries:
            try:
                # ThreadedConnectionPool, not SimpleConnectionPool: Simple has no
                # locking, so two threads (Flask dev server, or gunicorn --threads)
                # can grab the same connection and corrupt the wire protocol.
                return pool.ThreadedConnectionPool(minconn=minconn,
                                                   maxconn=maxconn,
                                                   **cnn)
            except psycopg2.DatabaseError as e:
                last_error = e
                print(f'Database error opening conn pool (attempt {attempts}/{max_retries}): {e}')
                #logging.exception(f'Database error encountered: {e}')
                time.sleep(10)
                attempts += 1
        # Fail FAST instead of returning None: a worker that cannot reach the
        # database should die at boot (gunicorn restarts it, EB flags the
        # instance) rather than come up and 500 every request.
        raise RuntimeError(
            f'Could not create connection pool after {max_retries} attempts'
        ) from last_error

    @classmethod
    def initialize_pool(cls, cnn):
        if cls.connection_pool is None:
            cls.connection_pool = cls.create_connection_pool(cnn)
            cls._pool_pid = os.getpid()
            cls._pool_creds = cnn

    @classmethod
    def is_pool_ready(cls):
        return cls.connection_pool is not None

    @classmethod
    def _ensure_pool_for_this_process(cls):
        # Fork guard: a pool created before a fork leaves parent and children
        # sharing the same sockets -> interleaved responses, protocol errors.
        # If we are not the process that built the pool, build a fresh one.
        # Deliberately do NOT close the inherited connections here: closing
        # them from the child would tear down the parent's sockets too.
        if cls.connection_pool is not None and cls._pool_pid != os.getpid():
            print(f'Connection pool was built in pid {cls._pool_pid}; '
                  f'rebuilding for pid {os.getpid()}')
            cls.connection_pool = cls.create_connection_pool(cls._pool_creds)
            cls._pool_pid = os.getpid()

    @contextmanager
    def get_connection(self):
        if self.connection_pool is None:
            raise ValueError("Connection pool not initialized")
        self._ensure_pool_for_this_process()

        conn = self.connection_pool.getconn()
        broken = False
        try:
            print("Acquiring connection pool thread")
            # logging.info("Acquiring connection pool thread")
            yield conn
        except Exception:
            # Roll back the failed transaction BEFORE the connection goes back
            # to the pool, so it is never handed to the next caller mid-abort.
            try:
                conn.rollback()
            except Exception:
                broken = True  # rollback itself failed: connection is unusable
            raise
        finally:
            # close=True discards a broken connection instead of pooling it;
            # the pool opens a replacement on the next getconn.
            self.connection_pool.putconn(conn, close=broken)

    def fetch_proc(self, query, params):
        attempts = 1
        last_error = None
        while attempts <= self.max_retries:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    return cursor.fetchall()
            except psycopg2.DatabaseError as e:
                last_error = e
                print(f'Database error encountered when fetching data for {query} and {params}: {e}')
                time.sleep(10)
                # logging.exception(f'Database error encountered when fetching data for {query} and {params}: {e}')
                attempts+=1
            except Exception as e:
                last_error = e
                print(f'Unexpected error encountered when fetching data for {query} and {params}: {e}')
                time.sleep(10)
                # logging.exception(f'Database error encountered when fetching data for {query} and {params}: {e}')
                attempts+=1

        # Raise instead of returning a sentinel: a silent 1 here is how DB
        # outages were surfacing as 200 "success" responses upstream.
        raise DatabaseOperationError(
            f'fetch failed after {self.max_retries} attempts: {query}') from last_error

    def store_proc(self, query, params) -> int:
        attempts = 1
        last_error = None

        while attempts <= self.max_retries:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    cursor.commit()  # Commit the transaction after successful execution
                    return 0 # success
            except psycopg2.DatabaseError as e:
                last_error = e
                print(f'Database error encountered for {query} and {params}: {e}')
                # logging.exception(f'Database error encountered for {query} and {params}: {e}')
                time.sleep(10)
                attempts+=1

            except Exception as e:
                last_error = e
                print(f'Unexpected error encountered for {query} and {params}: {e}')
                time.sleep(10)
                # logging.exception(f'Unexpected error encountered for {query} and {params}: {e}')
                attempts+=1

        raise DatabaseOperationError(
            f'store failed after {self.max_retries} attempts: {query}') from last_error
