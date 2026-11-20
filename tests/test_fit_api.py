# 역할: 핏 API의 실제 판정 연결·모든 사이즈 조회·누락 데이터 처리를 DB 호출 모의로 검사합니다.
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'garment/src'))
from api import fit as module
from ease_check import MEASURES_SQL, sizes_from_db_rows, check_all_sizes


class FitAPITests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(module.router)
        app.dependency_overrides[module.principal] = lambda: 'test'
        self.client = TestClient(app)
        self.body = {'chest_girth_cm':98., 'waist_girth_cm':82., 'hip_girth_cm':96.}

    def call(self, rows, catalog, **changes):
        payload = {'item_code':'TEST', 'size_label':'M', **self.body, **changes}
        with patch.object(module, 'query', side_effect=[rows, catalog]) as query, \
             patch.object(module.brand_catalog, 'product', return_value=(None,[])):
            response = self.client.post('/fit', json=payload)
        self.assertEqual(query.call_args_list[0].args, (MEASURES_SQL, ('TEST',)))
        self.assertEqual(query.call_args_list[1].args[1], ('TEST',))
        return response

    def test_all_sizes_and_unchanged_engine_response(self):
        rows = [dict(category='상의', size_label=label, region='KR', measure_code='chest_width', basis='garment', value_cm=width)
                for label,width in [('S',50),('M',53),('L',57)]]
        catalog = [dict(category='상의',size_label=label,region='KR') for label in ('S','M','L')]
        response = self.call(rows, catalog)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(), check_all_sizes('상의',self.body,sizes_from_db_rows(rows),'M'))
        self.assertEqual(response.json()['recommended_size'],'M')
        self.assertEqual(response.json()['selected']['parts'][0]['ease_cm'],8.)

    def test_bottom_and_missing_body(self):
        rows = [dict(size_label='M',region='KR',basis='garment',measure_code=key,value_cm=value)
                for key,value in [('waist_width',43),('hip_width',50)]]
        catalog = [dict(category='하의',size_label='M',region='KR')]
        response = self.call(rows,catalog)
        self.assertEqual(response.json()['selected']['verdict'],'FIT')
        response = self.call(rows,catalog,waist_girth_cm=None,hip_girth_cm=None)
        self.assertEqual(response.json()['selected']['verdict'],'UNDETERMINED')
        self.assertEqual(response.json()['fit_sizes'],[])

    def test_missing_garment_values_returns_undetermined(self):
        response = self.call([], [dict(category='하의',size_label='M',region='KR')])
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['selected']['verdict'],'UNDETERMINED')
        self.assertIsNone(response.json()['recommended_size'])

    def test_unknown_product_or_size(self):
        self.assertEqual(self.call([],[]).status_code,404)
        self.assertEqual(self.call([],[dict(category='상의',size_label='L',region='KR')]).status_code,422)

    def test_validation_and_authentication(self):
        with patch.object(module,'query') as query:
            self.assertEqual(self.client.post('/fit',json={'item_code':' ', 'size_label':'M'}).status_code,422)
            self.assertEqual(self.client.post('/fit',json={'item_code':'TEST','size_label':'M','chest_girth_cm':True}).status_code,422)
            query.assert_not_called()
        app=FastAPI();app.include_router(module.router)
        self.assertEqual(TestClient(app).post('/fit',json={'item_code':'TEST','size_label':'M'}).status_code,401)


if __name__ == '__main__':
    unittest.main()
