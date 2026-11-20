# 역할: category·측정 별칭 기반 템플릿 매핑과 모호한 소매 기준 거절을 검사합니다.
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'garment/src/core/catalog_mapping.py'
SPEC = importlib.util.spec_from_file_location('catalog_mapping_test', PATH)
mapping = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mapping)


class CatalogMappingTests(unittest.TestCase):
    def test_category_and_uniqlo_center_back(self):
        result = mapping.generation_settings('상의', ['sleeve-length-cb'])
        self.assertEqual(result, {'kind':'crewneck','template_id':'body_center_back_v19','sleeve_basis':'center_back'})

    def test_standard_shoulder_aliases(self):
        for alias in ['소매길이','sleeve-length','そで丈']:
            with self.subTest(alias=alias):
                self.assertEqual(mapping.generation_settings('상의',[alias])['sleeve_basis'],'shoulder')

    def test_bottoms_do_not_need_sleeve_metadata(self):
        self.assertEqual(mapping.generation_settings('하의',[]),
                         {'kind':'slacks','template_id':'black_midrise_straight_v1','sleeve_basis':'none'})

    def test_missing_conflicting_or_body_measurement_rejected(self):
        for aliases in [[],['unknown'],['arm_length'],['sleeve-length','sleeve-length-cb']]:
            with self.subTest(aliases=aliases), self.assertRaises(ValueError):
                mapping.generation_settings('상의',aliases)

    def test_other_categories_are_not_silently_mapped(self):
        for category in ['키즈 상의','속옷',None,'']:
            with self.subTest(category=category), self.assertRaises(ValueError):
                mapping.category_template(category)
