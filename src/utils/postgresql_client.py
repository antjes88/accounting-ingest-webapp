import atexit
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extensions import cursor as PgCursor
from psycopg2.pool import ThreadedConnectionPool


class PostgresSQLClient(ABC):
    _pools: Dict[Tuple[str, int, str, str], ThreadedConnectionPool] = {}
    _pool_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        host: str,
        database_name: str,
        user_name: str,
        user_password: str,
        port: int = 5432,
        minconn: int = 1,
        maxconn: int = 10,
    ) -> None:
        self.host: str = host
        self.database: str = database_name
        self.user: str = user_name
        self.password: str = user_password
        self.port: int = port
        self.minconn: int = minconn
        self.maxconn: int = maxconn

    @property
    def _pool_key(self) -> Tuple[str, int, str, str]:
        return (self.host, self.port, self.database, self.user)

    def _get_pool(self) -> ThreadedConnectionPool:
        with self._pool_lock:
            pool = self._pools.get(self._pool_key)
            if pool is None or pool.closed:
                pool = ThreadedConnectionPool(
                    minconn=self.minconn,
                    maxconn=self.maxconn,
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    port=self.port,
                )
                self._pools[self._pool_key] = pool
            return pool

    @abstractmethod
    def create_connection(self) -> Tuple[PgCursor, PgConnection]:
        raise NotImplementedError

    def close_connection(
        self, cursor: Optional[PgCursor], conn: Optional[PgConnection]
    ) -> None:
        if cursor and not cursor.closed:
            try:
                cursor.close()
            except Exception:
                pass

        if conn:
            with self._pool_lock:
                pool = self._pools.get(self._pool_key)

            if pool and not pool.closed:
                if conn.closed:
                    pool.putconn(conn, close=True)
                else:
                    try:
                        conn.rollback()
                        pool.putconn(conn, close=False)
                    except Exception:
                        try:
                            pool.putconn(conn, close=True)
                        except Exception:
                            pass
            else:
                if not conn.closed:
                    conn.close()

    def execute(self, statement: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        conn, cursor, error = None, None, None
        try:
            cursor, conn = self.create_connection()
            if params:
                cursor.execute(statement, params)
            else:
                cursor.execute(statement)
            conn.commit()
        except psycopg2.Error as e:
            error = e
        finally:
            self.close_connection(cursor, conn)
            if error:
                raise Exception(error)

    def query(
        self, statement: str, params: Optional[Tuple[Any, ...]] = None
    ) -> List[Tuple[Any, ...]]:
        conn, cursor, error = None, None, None
        try:
            cursor, conn = self.create_connection()
            if params:
                cursor.execute(statement, params)
            else:
                cursor.execute(statement)
            data = cursor.fetchall()
            conn.commit()
        except psycopg2.Error as e:
            error = e
        finally:
            self.close_connection(cursor, conn)
            if error:
                raise Exception(error)

        return data

    def close(self) -> None:
        with self._pool_lock:
            pool = self._pools.pop(self._pool_key, None)
            if pool and not pool.closed:
                pool.closeall()

    @classmethod
    def close_all_pools(cls) -> None:
        with cls._pool_lock:
            for pool in cls._pools.values():
                if not pool.closed:
                    pool.closeall()
            cls._pools.clear()


class PostgresGCPClient(PostgresSQLClient):

    def __init__(
        self,
        host: str,
        database_name: str,
        user_name: str,
        user_password: str,
        port: int = 5432,
        minconn: int = 1,
        maxconn: int = 10,
    ) -> None:
        super().__init__(
            host=host,
            database_name=database_name,
            user_name=user_name,
            user_password=user_password,
            port=port,
            minconn=minconn,
            maxconn=maxconn,
        )
        self.vendor: str = "GCP"

    def create_connection(self) -> Tuple[PgCursor, PgConnection]:
        cursor, conn = None, None
        try:
            pool = self._get_pool()
            conn = pool.getconn()
            cursor = conn.cursor()
        except (psycopg2.Error, Exception) as e:
            self.close_connection(cursor, conn)
            raise Exception(e)

        return cursor, conn


atexit.register(PostgresSQLClient.close_all_pools)
