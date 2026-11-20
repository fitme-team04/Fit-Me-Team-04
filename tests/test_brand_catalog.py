# 역할: 실제 SQL에서 읽은 상품 치수 스냅샷으로 브랜드 조회·환산·3D·핏 API 연결을 검증합니다.
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'garment/src'))
from database import brand_catalog
from api import garments, fit

DATA=json.loads((Path(__file__).parent/'fixtures/brand_catalog.json').read_text(encoding='utf-8'))


def brand_query(sql,params=()):
    for table,rows in DATA.items():
        if 'garment.'+table in sql:
            if 'COUNT(*) AS size_count' in sql:
                codes=sorted({row['product_id'] for row in rows})
                return [dict(category=(group:=[row for row in rows if row['product_id']==code])[0]['category'],
                             product_id=code,product_name=group[0]['product_name'],
                             source_name=group[0]['source_name'],size_count=len(group)) for code in codes]
            return [row.copy() for row in rows if not params or row['product_id']==params[0]]
    raise AssertionError('Unexpected SQL')


class BrandCatalogTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(garments.app)
        self.headers={'X-FitMe-Subject':'test'}

    def test_real_bottom_rows_convert_to_four_inputs(self):
        count=0
        for rows in DATA.values():
            for row in rows:
                if row['category']!='bottoms':continue
                spec=brand_catalog.spec_from_row(row)
                self.assertEqual(set(spec),{'waist_width','hip_width','thigh_width','inseam'})
                self.assertEqual(spec['waist_width'],row['waist_girth_cm']/2)
                self.assertEqual(spec['hip_width'],row['hip_girth_cm']/2)
                self.assertEqual(spec['thigh_width'],row['thigh_girth_cm']/2)
                self.assertEqual(spec['inseam'],row['inseam_cm'])
                count+=1
        self.assertGreater(count,0)

    def test_all_three_bottom_products_reach_generation(self):
        for rows in DATA.values():
            row=next(row for row in rows if row['category']=='bottoms')
            with self.subTest(item_code=row['product_id']), \
                 patch.object(garments,'query',return_value=[]), \
                 patch.object(brand_catalog,'query',side_effect=brand_query), \
                 patch.object(garments,'render',return_value={'status':'ready'}) as render, \
                 patch.object(garments,'resolve_template'):
                response=self.client.post('/api/garments',json={'item_code':row['product_id'],'size_label':row['size_label']},headers=self.headers)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(render.call_args.args[0]['spec'],{})
                self.assertEqual(render.call_args.args[0]['measurement_notes'],row['notes'])

    def test_brand_table_tops_are_not_used_for_generation(self):
        for rows in DATA.values():
            row=next(row for row in rows if row['category']=='tops')
            with patch.object(garments,'query',return_value=[]),patch.object(brand_catalog,'query',side_effect=brand_query),patch.object(garments,'render') as render:
                response=self.client.post('/api/garments',json={'item_code':row['product_id'],'size_label':row['size_label']},headers=self.headers)
                self.assertEqual(response.status_code,404)
                render.assert_not_called()

    def test_fit_uses_brand_circumferences_once(self):
        row=next(row for row in DATA['size_ziozia'] if row['category']=='bottoms')
        with patch.object(fit,'query',return_value=[]),patch.object(brand_catalog,'query',side_effect=brand_query):
            response=self.client.post('/fit',json={'item_code':row['product_id'],'size_label':row['size_label'],
                'waist_girth_cm':row['waist_girth_cm']-5,'hip_girth_cm':row['hip_girth_cm']-5},headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        selected=response.json()['selected']
        self.assertEqual(selected['verdict'],'FIT')
        self.assertEqual([p['ease_cm'] for p in selected['parts']],[5.,5.])
        self.assertEqual(len(response.json()['all_sizes']),sum(r['category']=='bottoms' for r in DATA['size_ziozia']))

    def test_sizes_keep_exact_labels_and_no_fake_numeric_ids(self):
        with patch.object(garments,'query',return_value=[]),patch.object(brand_catalog,'query',side_effect=brand_query):
            response=self.client.get('/api/garments/by-item/ABG4PP1110DNV/sizes')
        self.assertEqual(response.status_code,200)
        self.assertTrue(all(row['size_id'] is None for row in response.json()))
        expected={row['size_label'] for row in DATA['size_ziozia'] if row['product_id']=='ABG4PP1110DNV'}
        self.assertEqual({row['size_label'] for row in response.json()},expected)

    def test_brand_catalog_exposes_only_three_bottom_products(self):
        with patch.object(brand_catalog,'query',side_effect=brand_query):
            response=self.client.get('/api/garments/brand-catalog')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()),3)
        self.assertEqual(sum(row['size_count'] for row in response.json()),25)

    def test_bottom_fit_uses_actual_measurements(self):
        for rows in DATA.values():
            for code in {row['product_id'] for row in rows}:
                row=next(row for row in rows if row['product_id']==code)
                if row['category']!='bottoms':continue
                body={key:row[key]-5 if row[key] is not None else None for key in ('chest_girth_cm','waist_girth_cm','hip_girth_cm')}
                with self.subTest(code=code),patch.object(fit,'query',return_value=[]),patch.object(brand_catalog,'query',side_effect=brand_query):
                    response=self.client.post('/fit',json={'item_code':code,'size_label':row['size_label'],**body},headers=self.headers)
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.json()['selected']['verdict'],'FIT')

    def test_brand_top_is_not_used_for_fit(self):
        with patch.object(fit,'query',return_value=[]),patch.object(brand_catalog,'query',side_effect=brand_query):
            response=self.client.post('/fit',json={'item_code':'1144989','size_label':'M','chest_girth_cm':98.},headers=self.headers)
        self.assertEqual(response.status_code,404)


if __name__=='__main__':unittest.main()
