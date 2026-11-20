"""Regression checks for the buyer's two-field comparison, with the team's sample profiles."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import listing_fit
import team_bridge


def compare(weight, *, height=170, category="상의·아우터", rows=None, my_garment=None):
    if rows is None:
        rows = [("가슴단면", 55, "시연용 예시")]
    request = listing_fit.ListingFitRequest(
        category=category, rows=rows, body={"height_cm": height, "weight_kg": weight},
        my_garment=my_garment or {})
    return listing_fit.recommend_listing(request)


class ResaleFitV2Test(unittest.TestCase):
    def test_sam_measures_are_used_instead_of_height_weight_estimate(self):
        request=listing_fit.ListingFitRequest(category="상의·아우터",
            rows=[("가슴단면",60,"카탈로그")],
            body={"height_cm":170,"weight_kg":65,"measures":{"chest_girth":100},
                  "source":"생성된 SAM 신체 메시 실측"})
        with patch.object(team_bridge,'estimate_from_height_weight',side_effect=AssertionError('Must use SAM')):
            result=listing_fit.recommend_listing(request)
        row=result['evidence'][0]
        self.assertEqual(row['reference_cm'],100)
        self.assertEqual(row['difference_cm'],20)

    def setUp(self):
        self.enterContext(patch.object(team_bridge.sizekorea_reference, "configured_profiles", return_value=None))
        self.enterContext(patch.object(team_bridge, "current_mode", return_value="demo"))

    def test_adjacent_weights_get_the_same_ease_check_verdict(self):
        # V1 gave 14.6 cm for 78 kg and 5.5 cm for 79 kg on the same 55 cm top.
        lighter, heavier = compare(78), compare(79)
        for result in (lighter, heavier):
            self.assertIn(result["ease_check"]["verdict"], ("FIT", "NO_FIT"))
            self.assertEqual(result["title"], result["ease_check"]["message_ko"])
            self.assertEqual(result["evidence"][0]["source"], "시연용 예시")
        self.assertEqual(lighter["ease_check"]["verdict"], heavier["ease_check"]["verdict"])
        change = abs(lighter["evidence"][0]["difference_cm"] - heavier["evidence"][0]["difference_cm"])
        self.assertLess(change, 1)

    def test_sparse_coverage_offers_a_reference_on_the_same_listing(self):
        unavailable = compare(50, height=155)
        self.assertEqual(unavailable["status"], "hold")
        self.assertFalse(unavailable["evidence"])
        self.assertEqual(unavailable["reference_field"], "가슴단면")
        reference = compare(50, height=155, my_garment={"가슴단면": 54})
        self.assertEqual(reference["basis"], "my_garment")
        self.assertEqual(reference["evidence"][0]["difference_cm"], 1)
        self.assertEqual(reference["status"], "recommended")

    def test_clearly_narrow_garment_is_no_fit_with_ease_check_message(self):
        result = compare(78, rows=[("가슴단면", 35, "직접 실측")])
        self.assertEqual(result["status"], "check")
        self.assertEqual(result["ease_check"]["verdict"], "NO_FIT")
        self.assertEqual(result["ease_check"]["parts"][0]["status"], "TOO_TIGHT")
        self.assertTrue(result["title"].startswith("맞지 않습니다"))
        self.assertNotIn("reference_field", result)

    def test_bottoms_are_not_judged(self):
        result = compare(78, category="하의", rows=[("허리단면", 42, "직접 실측"), ("엉덩이단면", 52, "직접 실측")])
        self.assertEqual(result["status"], "hold")
        self.assertNotIn("ease_check", result)

    def test_no_fit_selection_field_any_more(self):
        self.assertNotIn("fit", listing_fit.ListingFitRequest.model_fields)


class EaseSizesTest(unittest.TestCase):
    """구매자 피팅룸 /api/resale/ease: 한 상품의 사이즈를 ease_check 결과 그대로 돌려준다."""

    CHART = {"mode": "db", "sizes": [
        {"region": "KR", "label": "S", "measures": {"가슴단면": 50.0}},
        {"region": "KR", "label": "M", "measures": {"가슴단면": 53.0, "총장": 69.0}},
        {"region": "KR", "label": "L", "measures": {"가슴단면": 56.0}},
        {"region": "KR", "label": "XXL", "measures": {"가슴단면": 64.0}},
        {"region": "US", "label": "M", "measures": {"가슴단면": 56.0}},
        {"region": "KR", "label": "XS", "measures": {}},
    ]}

    def ease(self, chest=100.08, **fields):
        request = listing_fit.EaseRequest(**{"garment_id": 6, "category": "상의", "size_label": "M",
                                             "height_cm": 175, "weight_kg": 70, **fields})
        estimate = ({"chest_girth": chest}, {"chest_girth": 2.0}, {"chest_girth": 5}, [], "테스트 표본")
        with patch("resale.size_chart", return_value=self.CHART), \
             patch.object(team_bridge, "estimate_from_height_weight", return_value=estimate):
            return listing_fit.ease_sizes(request)

    def test_result_is_ease_check_output_with_measured_kr_sizes_only(self):
        result = self.ease()
        self.assertEqual(result["selected"]["verdict"], "FIT")
        self.assertEqual(result["selected"]["message_ko"], "입을 수 있습니다. 가슴둘레 여유 +5.9cm")
        self.assertEqual(result["recommended_size"], "M")
        self.assertEqual([size["size_label"] for size in result["all_sizes"]], ["S", "M", "L", "XXL"])
        statuses = {size["size_label"]: size["verdict"] for size in result["all_sizes"]}
        self.assertEqual(statuses["S"], "NO_FIT")
        self.assertEqual(statuses["XXL"], "NO_FIT")
        self.assertEqual(result["body"]["chest_girth_cm"], 100.1)

    def test_too_small_selected_size_recommends_another(self):
        result = self.ease(size_label="S")
        self.assertEqual(result["selected"]["verdict"], "NO_FIT")
        self.assertEqual(result["selected"]["parts"][0]["status"], "TOO_TIGHT")
        self.assertEqual(result["recommended_size"], "M")

    def test_non_kr_size_and_bottoms_are_undetermined(self):
        us = self.ease(region="US")
        self.assertEqual(us["selected"]["verdict"], "UNDETERMINED")
        bottoms = self.ease(category="하의")
        self.assertEqual(bottoms["selected"]["verdict"], "UNDETERMINED")
        self.assertIsNone(bottoms["recommended_size"])

    def test_missing_body_estimate_is_undetermined(self):
        result = self.ease(chest=None)
        self.assertEqual(result["selected"]["verdict"], "UNDETERMINED")
        self.assertTrue(result["selected"]["message_ko"].startswith("판정할 수 없습니다"))

    def test_missing_garment_width_does_not_suggest_buyer_remeasurement(self):
        result = compare(78, rows=[("총장", 70, "ML 결과 파일")])
        self.assertEqual(result["status"], "hold")
        self.assertNotIn("reference_field", result)

    def test_one_dress_measurement_compares_only_that_part(self):
        result = compare(78, category="원피스", rows=[("가슴단면", 55, "직접 실측"), ("허리단면", 44, "직접 실측")],
                         my_garment={"허리단면": 42})
        self.assertEqual(result["basis"], "my_garment")
        self.assertEqual(result["status"], "hold")
        self.assertIn("2 cm", result["title"])
        self.assertIn("가슴단면", result["explanation"])


if __name__ == "__main__":
    unittest.main()
