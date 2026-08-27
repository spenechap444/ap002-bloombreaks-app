import psycopg2
from psycopg2 import pool
import os
import time
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


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
                logger.error('Database error opening conn pool (attempt %d/%d): %s',
                             attempts, max_retries, e)
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
    def health_check(cls, statement_timeout_ms=2000):
        """Round-trip a trivial query. Returns (ok: bool, detail: str).

        Deliberately does NOT go through fetch_proc. That path retries five
        times with a 10s sleep between attempts, so an unreachable database
        would hold the request ~50s and the load balancer would give up long
        before getting an answer. A health check makes exactly one attempt and
        answers immediately, either way.
        """
        if cls.connection_pool is None:
            return False, 'connection pool not initialized'

        try:
            cls._ensure_pool_for_this_process()
        except Exception as e:
            return False, f'pool rebuild failed: {type(e).__name__}: {e}'

        conn = None
        broken = False
        try:
            conn = cls.connection_pool.getconn()
            with conn.cursor() as cursor:
                # Bound the query so a hung backend fails the check instead of
                # hanging the worker. LOCAL = scoped to this transaction, so it
                # cannot leak onto the next borrower of this connection.
                cursor.execute(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)};")
                cursor.execute('SELECT 1;')
                row = cursor.fetchone()
            if row != (1,):
                return False, f'unexpected response to SELECT 1: {row!r}'
            # End the implicit transaction so the connection returns to the
            # pool idle rather than idle-in-transaction.
            conn.rollback()
            return True, 'ok'
        except Exception as e:
            broken = True
            return False, f'{type(e).__name__}: {e}'
        finally:
            if conn is not None:
                try:
                    # close=True on failure: discard a suspect connection rather
                    # than handing it to the next caller.
                    cls.connection_pool.putconn(conn, close=broken)
                except Exception as e:
                    logger.error('health_check: failed to return connection to pool: %s', e)

    @classmethod
    def _ensure_pool_for_this_process(cls):
        # Fork guard: a pool created before a fork leaves parent and children
        # sharing the same sockets -> interleaved responses, protocol errors.
        # If we are not the process that built the pool, build a fresh one.
        # Deliberately do NOT close the inherited connections here: closing
        # them from the child would tear down the parent's sockets too.
        if cls.connection_pool is not None and cls._pool_pid != os.getpid():
            logger.info('Connection pool was built in pid %s; rebuilding for pid %s',
                        cls._pool_pid, os.getpid())
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
            logger.debug('Acquired connection from pool')
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
                logger.warning('Database error fetching %s with %s: %s', query, params, e)
                time.sleep(10)
                attempts+=1
            except Exception as e:
                last_error = e
                logger.warning('Unexpected error fetching %s with %s: %s', query, params, e)
                time.sleep(10)
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
                    # conn.commit(), not cursor.commit() - psycopg2 cursors have
                    # no commit(); the AttributeError was being swallowed by the
                    # generic except below and retried as if it were a DB fault.
                    conn.commit()
                    return 0 # success
            except psycopg2.DatabaseError as e:
                last_error = e
                logger.warning('Database error storing %s with %s: %s', query, params, e)
                time.sleep(10)
                attempts+=1

            except Exception as e:
                last_error = e
                logger.warning('Unexpected error storing %s with %s: %s', query, params, e)
                time.sleep(10)
                attempts+=1

        raise DatabaseOperationError(
            f'store failed after {self.max_retries} attempts: {query}') from last_error
