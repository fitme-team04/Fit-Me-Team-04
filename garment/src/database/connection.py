# 역할: 환경변수로 Azure SQL 연결을 구성하고 쿼리·트랜잭션을 수행합니다.
"""Azure SQL connection shared by API and ML. Credentials stay in environment."""
import os
import re
import time
from contextlib import closing, contextmanager
import pyodbc


class DatabaseUnavailable(RuntimeError):
    """Connection setup remained unavailable; contains no ODBC credentials."""


def _transient_connect_error(error):
    state=str(error.args[0]).strip().upper() if error.args else ''
    if state in {'HYT00','HYT01','08S01'}:
        return True
    return bool(re.search(r'\b(?:40613|40197|40501)\b',' '.join(str(value) for value in error.args)))


def _connect():
    settings=connection_string()
    try:
        return pyodbc.connect(settings,timeout=10,autocommit=False)
    except pyodbc.Error as error:
        if not _transient_connect_error(error):
            raise
    # Only establishing a connection is replayed. The transaction body and
    # commit below each execute once, even after an ambiguous ODBC failure.
    time.sleep(2)
    try:
        return pyodbc.connect(settings,timeout=45,autocommit=False)
    except pyodbc.Error:
        raise DatabaseUnavailable('Database connection is temporarily unavailable') from None

def connection_string():
    explicit = os.getenv("AZURE_SQL_CONNECTION_STRING", "").strip()
    if explicit:
        return explicit
    authentication = os.getenv('AZURE_SQL_AUTHENTICATION', 'SqlPassword').strip()
    if authentication not in ('SqlPassword', 'ActiveDirectoryMsi'):
        raise ValueError('AZURE_SQL_AUTHENTICATION must be SqlPassword or ActiveDirectoryMsi')
    names = ("AZURE_SQL_SERVER", "AZURE_SQL_DATABASE")
    if authentication == 'SqlPassword':
        names += ("AZURE_SQL_USERNAME", "AZURE_SQL_PASSWORD")
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise ValueError("Missing database settings: " + ", ".join(missing))
    def quoted(value):
        return "{" + value.replace("}", "}}") + "}"
    server = os.environ["AZURE_SQL_SERVER"]
    if not server.startswith("tcp:"):
        server = "tcp:" + server
    if "," not in server:
        server += ",1433"
    pairs = {
        "DRIVER": "ODBC Driver 18 for SQL Server", "SERVER": server,
        "DATABASE": os.environ["AZURE_SQL_DATABASE"],
        "Authentication": authentication,
        "Encrypt": "yes", "TrustServerCertificate": "no", "LongAsMax": "yes",
    }
    if authentication == 'SqlPassword':
        pairs.update(UID=os.environ['AZURE_SQL_USERNAME'], PWD=os.environ['AZURE_SQL_PASSWORD'])
    elif authentication == 'ActiveDirectoryMsi' and os.getenv('AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID', '').strip():
        pairs['UID'] = os.environ['AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID'].strip()
    return ";".join(key + "=" + quoted(value) for key, value in pairs.items()) + ";"

@contextmanager
def transaction():
    connection = _connect()
    try:
        connection.timeout = 90
        with closing(connection.cursor()) as cursor:
            yield cursor
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()

def query(sql, parameters=()):
    with transaction() as cursor:
        cursor.execute(sql, *parameters)
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
