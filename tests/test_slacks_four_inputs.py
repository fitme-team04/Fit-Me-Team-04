# 역할: 하의 네 입력 계약·원형 비율 파생과 실제 상품 API의 누락 필드 처리를 검사합니다.
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.garment_specs import validate_spec, complete_slacks_spec
from api import garments


class SlacksFourInputTests(unittest.TestCase):
    spec={'waist_width':42.,'hip_width':52.,'thigh_width':32.,'inseam':72.}

    def test_only_four_values_are_required(self):
        self.assertEqual(validate_spec('slacks',self.spec,'none'),self.spec)
        self.assertEqual(validate_spec('slacks',{**self.spec,'front_rise':None,'knee_width':-1,'hem_width':900},'none'),self.spec)
        for key in self.spec:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_spec('slacks',{k:v for k,v in self.spec.items() if k!=key},'none')

    def test_derived_values_follow_connected_measurements(self):
        reference={**self.spec,'front_rise':30.,'knee_width':26.,'hem_width':25.}
        changed={**self.spec,'hip_width':57.2,'thigh_width':35.2}
        result=complete_slacks_spec(changed,reference)
        self.assertAlmostEqual(result['front_rise'],33.)
        self.assertAlmostEqual(result['knee_width'],28.6)
        self.assertAlmostEqual(result['hem_width'],27.5)
        self.assertEqual(result['inseam'],72.)

    def test_four_value_reference_uses_consistent_default_ratios(self):
        result=complete_slacks_spec(self.spec,self.spec)
        expected=complete_slacks_spec(self.spec)
        self.assertEqual(result,expected)

    def test_api_generates_without_unused_database_measures(self):
        rows=[dict(garment_id=1,item_code='TEST',category='하의',source_name='test',
                   region='KR',size_label='M',measure_code=k,value_cm=v) for k,v in self.spec.items()]
        rows.append({**rows[0],'measure_code':'front_rise','value_cm':-999})
        with patch.object(garments,'query',return_value=rows), \
             patch.object(garments,'resolve_template'), \
             patch.object(garments,'render',return_value={'status':'ready'}) as render:
            response=TestClient(garments.app).post('/api/garments',json={'item_code':'TEST','size_id':1},headers={'X-FitMe-Subject':'test'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(render.call_args.args[0]['spec'],{})


if __name__=='__main__':unittest.main()
