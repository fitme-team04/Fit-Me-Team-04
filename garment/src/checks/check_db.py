# 역할: Azure SQL의 실상품·측정 별칭 테이블 접근을 읽기 전용으로 확인합니다.
"""Read-only connection/schema probe. Does not print credentials or driver messages."""
import sys
import pyodbc
from database.connection import query

def main():
    if "ODBC Driver 18 for SQL Server" not in pyodbc.drivers():
        print("FAIL: Microsoft ODBC Driver 18 is not installed.")
        return 1
    try:
        query("SELECT 1 AS connected")
        tables = ['garment.garments', 'garment.sizes', 'garment.measures', 'ref.measure_aliases']
        missing = []
        for table in tables:
            if query("SELECT OBJECT_ID(?, 'U') AS object_id", (table,))[0]["object_id"] is None:
                missing.append(table)
        if missing:
            print("CONNECTED, but required tables are missing or not visible: " + ", ".join(missing))
            return 2
        if query("SELECT COL_LENGTH(N'garment.garments',N'category') AS n")[0]['n'] is None:
            print('CONNECTED, but garment.garments.category is missing.')
            return 2
        print("PASS: Azure SQL connection and required table visibility. Write permissions are not tested.")
        return 0
    except ValueError as exc:
        print(str(exc))
    except pyodbc.Error:
        print("FAIL: Check server/database, credentials, SQL firewall, DNS/private endpoint and TLS certificate.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
