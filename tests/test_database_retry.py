# 역할: SQL 연결만 제한적으로 재시도하고 쿼리·commit을 재생하지 않으며 API 오류가 비밀을 노출하지 않는지 검사합니다.
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock, call, patch

import pyodbc
from fastapi.testclient import TestClient

SRC=Path(__file__).resolve().parents[1]/'garment/src'
sys.path.insert(0,str(SRC))
from api import garments
from api import fit as fit_api


class FakeError(Exception):
    pass


class FakeOperationalError(FakeError):
    pass


class ConnectionRetryTests(unittest.TestCase):
    def setUp(self):
        self.driver=ModuleType('pyodbc')
        self.driver.Error=FakeError;self.driver.OperationalError=FakeOperationalError
        self.driver.connect=MagicMock()
        with patch.dict(sys.modules,{'pyodbc':self.driver}):
            spec=importlib.util.spec_from_file_location('retry_database_under_test',SRC/'database/connection.py')
            self.database=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.database)
        self.connection=MagicMock();self.cursor=self.connection.cursor.return_value
        self.settings=patch.object(self.database,'connection_string',return_value='private connection settings')
        self.settings.start();self.addCleanup(self.settings.stop)

    def test_transient_connect_retries_once_before_executing_transaction(self):
        errors=[FakeOperationalError('HYT00','login timed out'),
                FakeError('42000','Database unavailable (40613)'),
                FakeError('08001','Service failed (40197)'),
                FakeError('HY000','Service busy (40501)')]
        for error in errors:
            self.driver.connect.reset_mock();self.connection.reset_mock()
            self.driver.connect.side_effect=[error,self.connection]
            with self.subTest(error=error.args[0]),patch.object(self.database.time,'sleep') as sleep:
                with self.database.transaction() as cursor:cursor.execute('SELECT 1')
            self.assertEqual(self.driver.connect.call_args_list,[
                call('private connection settings',timeout=10,autocommit=False),
                call('private connection settings',timeout=45,autocommit=False)])
            sleep.assert_called_once_with(2)
            self.cursor.execute.assert_called_once_with('SELECT 1')
            self.connection.commit.assert_called_once();self.connection.rollback.assert_not_called()
            self.connection.close.assert_called_once()
            self.assertEqual(self.connection.timeout,90)

    def test_non_transient_connection_is_not_retried_or_slept(self):
        for error in (FakeOperationalError('28000','Login denied'),FakeError('42000','Native error (140613)')):
            self.driver.connect.reset_mock();self.driver.connect.side_effect=error
            with self.subTest(state=error.args[0]),patch.object(self.database.time,'sleep') as sleep:
                with self.assertRaises(FakeError) as caught:
                    with self.database.transaction():self.fail('Connection must fail before transaction')
            self.assertIs(caught.exception,error)
            self.driver.connect.assert_called_once();sleep.assert_not_called()

    def test_second_connect_failure_is_sanitized_without_logging_credentials(self):
        secret='never-print-this-password'
        self.driver.connect.side_effect=[FakeOperationalError('HYT00',secret),FakeOperationalError('HYT00',secret)]
        output=io.StringIO()
        with patch.object(self.database.time,'sleep'),contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            with self.assertRaises(self.database.DatabaseUnavailable) as caught:
                with self.database.transaction():self.fail('No connection was established')
        self.assertEqual(self.driver.connect.call_count,2)
        self.assertEqual(output.getvalue(),'')
        self.assertNotIn(secret,str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)
        self.connection.cursor.assert_not_called()

    def test_query_failure_never_reconnects_or_replays_the_query(self):
        self.driver.connect.return_value=self.connection
        failure=FakeOperationalError('HYT00','Statement timeout after connection')
        self.cursor.execute.side_effect=failure
        with patch.object(self.database.time,'sleep') as sleep,self.assertRaises(FakeOperationalError):
            self.database.query('UPDATE example SET value=?',(1,))
        self.driver.connect.assert_called_once();self.cursor.execute.assert_called_once_with('UPDATE example SET value=?',1)
        self.connection.commit.assert_not_called();self.connection.rollback.assert_called_once()
        self.cursor.close.assert_called_once();self.connection.close.assert_called_once();sleep.assert_not_called()

    def test_commit_failure_never_replays_the_transaction(self):
        self.driver.connect.return_value=self.connection
        self.connection.commit.side_effect=FakeOperationalError('08S01','Commit acknowledgment lost')
        entered=[]
        with patch.object(self.database.time,'sleep') as sleep,self.assertRaises(FakeOperationalError):
            with self.database.transaction() as cursor:
                entered.append(True);cursor.execute('INSERT INTO example VALUES (?)',1)
        self.assertEqual(entered,[True])
        self.driver.connect.assert_called_once();self.cursor.execute.assert_called_once()
        self.connection.commit.assert_called_once();self.connection.rollback.assert_called_once()
        self.connection.close.assert_called_once();sleep.assert_not_called()


class DatabaseAPITests(unittest.TestCase):
    def test_database_failures_return_503_without_odbc_details(self):
        secret='never-print-this-password'
        cases=[(garments,pyodbc.OperationalError('HYT00',secret),'/api/garments',None),
               (fit_api,garments.DatabaseUnavailable(secret),'/fit',{'item_code':'ITEM','size_label':'M'})]
        for module,error,path,payload in cases:
            with self.subTest(path=path),patch.object(module,'query',side_effect=error) as query:
                client=TestClient(garments.app)
                response=(client.get(path) if payload is None else client.post(path,json=payload,headers={'X-FitMe-Subject':'test'}))
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.headers['Retry-After'],'5')
            self.assertIn('데이터베이스',response.json()['detail'])
            self.assertNotIn(secret,response.text);self.assertNotIn('HYT00',response.text)
            query.assert_called_once()


if __name__=='__main__':unittest.main()
