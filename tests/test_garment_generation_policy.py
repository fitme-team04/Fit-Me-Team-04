# 역할: SAM 피팅은 DB 치수를 생략하고 신체 없는 기존 상의·하의 생성 정책은 유지하는지 검사합니다.
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from api import garments


class GenerationPolicyTests(unittest.TestCase):
    def test_sam_body_uses_catalog_template_without_db_measurements(self):
        for category,basis in [('상의','center_back'),('하의','none')]:
            rows=[dict(garment_id=1,item_code='ITEM',category=category,source_name='test',region='KR',size_label='M')]
            with self.subTest(category=category),patch.object(garments,'query',return_value=rows) as query, \
                 patch.object(garments,'validate_spec',side_effect=AssertionError('DB sizes must not be validated')), \
                 patch.object(garments,'generation_settings',side_effect=AssertionError('DB aliases must not select sizing')), \
                 patch.object(garments,'resolve_template',return_value={'sleeve_basis':basis}), \
                 patch.object(garments,'render',return_value={'status':'ready'}) as render:
                response=TestClient(garments.app).post('/api/garments',json={
                    'item_code':'ITEM','size_id':1,'body_model_id':'a'*64},headers={'X-FitMe-Subject':'test'})
            self.assertEqual(response.status_code,200,response.text)
            payload=render.call_args.args[0]
            self.assertEqual(payload['spec'],{})
            self.assertEqual(payload['geometry_mode'],'sam_body')
            self.assertEqual(payload['body_model_id'],'a'*64)
            self.assertEqual(payload['recipe']['sleeve_basis'],basis)
            query.assert_called_once()
            self.assertNotIn('garment.measures',query.call_args.args[0])
            self.assertNotIn('measure_aliases',query.call_args.args[0])

    def test_normalized_bottom_needs_no_measurements(self):
        rows=[dict(garment_id=1,item_code='BOTTOM',category='하의',source_name='test',region='KR',size_label='M',measure_code=None,value_cm=None)]
        with patch.object(garments,'query',return_value=rows),patch.object(garments,'resolve_template'),patch.object(garments,'render',return_value={'status':'ready'}) as render:
            response=TestClient(garments.app).post('/api/garments',json={'item_code':'BOTTOM','size_id':1},headers={'X-FitMe-Subject':'test'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(render.call_args.args[0]['spec'],{})

    def test_top_uses_measures_and_never_brand_values(self):
        values={'body_length':58.16,'garment_shoulder_width':39.06,'chest_width':55.05,'sleeve_length':48.05}
        rows=[dict(garment_id=1,item_code='TOP',category='상의',source_name='test',region='KR',size_label='M',measure_code=key,value_cm=value) for key,value in values.items()]
        with patch.object(garments,'query',side_effect=[rows,[{'alias_name':'sleeve-length'}]]),patch.object(garments.brand_catalog,'product') as brand,patch.object(garments,'resolve_template'),patch.object(garments,'render',return_value={'status':'ready'}) as render:
            response=TestClient(garments.app).post('/api/garments',json={'item_code':'TOP','size_id':1},headers={'X-FitMe-Subject':'test'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(render.call_args.args[0]['spec'],values)
        brand.assert_not_called()


if __name__=='__main__':unittest.main()
