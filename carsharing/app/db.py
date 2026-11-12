"""Connection pool, transaction helpers and retry logic."""
import os
import time
from contextlib import contextmanager

from psycopg import IsolationLevel
from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def init_pool() -> ConnectionPool:
    """Create the pool ONCE at application start-up (never inside a request)."""
    global _pool
    _pool = ConnectionPool(
        conninfo=os.environ["DATABASE_URL"],
        min_size=2,
        max_size=8,
        timeout=5.0,                      # PoolTimeout (-> HTTP 503) if no free connection
        kwargs={"row_factory": dict_row},  # rows come back as dicts
        open=True,
    )
    return _pool


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Pool is not initialised")
    return _pool


@contextmanager
def transaction():
    """READ COMMITTED transaction with explicit COMMIT / ROLLBACK."""
    with get_pool().connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


@contextmanager
def serializable():
    """SERIALIZABLE transaction. The isolation level is reset before the
    connection goes back to the pool so other requests are not affected."""
    with get_pool().connection() as conn:
        conn.isolation_level = IsolationLevel.SERIALIZABLE
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.isolation_level = None   # back to server default (READ COMMITTED)


def with_retry(fn, max_retries: int = 3):
    """Re-run a whole transaction when PostgreSQL reports a serialization failure (40001)."""
    for attempt in range(max_retries):
        try:
            return fn()
        except pg_errors.SerializationFailure:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.05 * 2 ** attempt)   # exponential back-off
