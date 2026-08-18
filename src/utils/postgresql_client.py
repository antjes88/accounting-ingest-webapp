import psycopg2
from abc import ABC, abstractmethod
from typing import Any, Tuple, List, Optional
from psycopg2.extensions import connection as PgConnection
from psycopg2.extensions import cursor as PgCursor


class PostgresSQLClient(ABC):

    @staticmethod
    def close_connection(
        cursor: Optional[PgCursor], conn: Optional[PgConnection]
    ) -> None:

        if cursor:
            cursor.close()
        if conn:
            conn.close()

    @abstractmethod
    def create_connection(self) -> Tuple[PgCursor, PgConnection]:

        raise NotImplementedError

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
        except psycopg2.Error as e:
            error = e
        finally:
            self.close_connection(cursor, conn)
            if error:
                raise Exception(error)

        return data


class PostgresGCPClient(PostgresSQLClient):
    def __init__(
        self,
        host: str,
        database_name: str,
        user_name: str,
        user_password: str,
        port: int = 5432,
    ) -> None:

        self.vendor: str = "GCP"
        self.host: str = host
        self.database: str = database_name
        self.user: str = user_name
        self.password: str = user_password
        self.port: int = port

    def create_connection(self) -> Tuple[PgCursor, PgConnection]:

        cursor, conn = None, None

        try:
            conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
            )
            cursor = conn.cursor()

        except psycopg2.Error as e:
            self.close_connection(cursor, conn)
            raise Exception(e)

        return cursor, conn
