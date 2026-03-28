import psycopg2
from abc import ABCMeta, abstractmethod
from typing import Any, Tuple, List


class PostgresSQLClient(metaclass=ABCMeta):

    @staticmethod
    def close_connection(cursor, conn):

        if cursor:
            cursor.close()
        if conn:
            conn.close()

    @abstractmethod
    def create_connection(self):

        raise NotImplementedError

    def execute(self, statement):

        conn, cursor, error = None, None, None
        try:
            cursor, conn = self.create_connection()
            cursor.execute(statement)
            conn.commit()
        except psycopg2.Error as e:
            error = e
        finally:
            self.close_connection(cursor, conn)
            if error:
                raise Exception(error)

    def query(self, statement) -> List[Tuple[Any, ...]]:

        conn, cursor, error = None, None, None
        try:
            cursor, conn = self.create_connection()
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
    def __init__(self, host, database_name, user_name, user_password, port=5432):

        self.vendor = "GCP"
        self.host = host
        self.database = database_name
        self.user = user_name
        self.password = user_password
        self.port = port

    def create_connection(self):

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
