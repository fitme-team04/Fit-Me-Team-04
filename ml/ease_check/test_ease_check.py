"""ease_check.py 테스트 - 상의 가슴 여유분 3~20cm 기준 FIT / NO_FIT / UNDETERMINED (v4, 하의 제외)"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))   # ease_check.py 와 같은 폴더
from ease_check import (MEASURES_SQL, body_from_ml_response, check_all_sizes, check_ease,  # noqa: E402
                        sizes_from_db_rows)

BODY = {"chest_girth_cm": 98.0}

# Azure SQL fitme-sql-dev > fitme, garment.garments·sizes·measures 실제 값 (2026-11-16 조회)
# UNIQLO 크루넥T item_code E422992-000, chest_width(가슴단면) — KR 일부 + US 1행
UNIQLO_ROWS = [
    {"item_code": "E422992-000", "category": "상의", "size_id": 2, "size_label": "S", "region": "KR",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 50.0},
    {"item_code": "E422992-000", "category": "상의", "size_id": 3, "size_label": "M", "region": "KR",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 53.0},
    {"item_code": "E422992-000", "category": "상의", "size_id": 4, "size_label": "L", "region": "KR",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 56.0},
    {"item_code": "E422992-000", "category": "상의", "size_id": 5, "size_label": "XL", "region": "KR",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 60.0},
    {"item_code": "E422992-000", "category": "상의", "size_id": 6, "size_label": "XXL", "region": "KR",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 64.0},
    {"item_code": "E422992-000", "category": "상의", "size_id": 10, "size_label": "M", "region": "US",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 56.0},
]
ML_RESPONSE = {"male": {"chest_girth_cm": 100.08, "chest_width_cm": 34.93,
                        "waist_girth_cm": 80.56, "hip_girth_cm": 95.98, "rise_arc_cm": 63.27}}


# --- 최소 3cm ---
def test_exactly_3cm_is_fit():
    assert check_ease("상의", BODY, {"chest_girth_cm": 101.0})["verdict"] == "FIT"


def test_under_3cm_is_too_tight():
    r = check_ease("상의", BODY, {"chest_girth_cm": 100.9})
    assert r["verdict"] == "NO_FIT" and r["parts"][0]["status"] == "TOO_TIGHT"
    assert r["parts"][0]["ease_cm"] == 2.9 and "작습니다" in r["message_ko"]


def test_rounding_does_not_turn_2_96_into_fit():
    # 여유 2.96cm 는 반올림하면 3.0 이지만, 비교는 반올림 전 값으로 → NO_FIT
    r = check_ease("상의", {"chest_girth_cm": 98.04}, {"chest_girth_cm": 101.0})
    assert r["verdict"] == "NO_FIT" and r["parts"][0]["ease_cm"] == 3.0


def test_float_error_at_exactly_3cm_is_fit():
    assert check_ease("상의", {"chest_girth_cm": 98.1}, {"chest_girth_cm": 101.1})["verdict"] == "FIT"


# --- 최대 20cm ---
def test_exactly_20cm_is_fit():
    r = check_ease("상의", {"chest_girth_cm": 100.0}, {"chest_girth_cm": 120.0})
    assert r["verdict"] == "FIT" and r["parts"][0]["status"] == "OK"


def test_over_20cm_is_too_loose():
    r = check_ease("상의", {"chest_girth_cm": 100.0}, {"chest_girth_cm": 120.1})
    assert r["verdict"] == "NO_FIT" and r["parts"][0]["status"] == "TOO_LOOSE"
    assert "너무 큽니다" in r["message_ko"]


# --- 판정 불가 ---
@pytest.mark.parametrize("body, garment", [
    ({}, {"chest_girth_cm": 110}),                                  # 몸 값 없음
    ({"chest_girth_cm": 98}, {}),                                   # 옷 값 없음
    ({"chest_girth_cm": 98}, {"chest_girth_cm": 53}),               # 단면 값 의심 (× 2 안 함)
    ({"chest_girth_cm": 500}, {"chest_girth_cm": 510}),             # 비정상 신체 값
    ({"chest_girth_cm": "abc"}, {"chest_girth_cm": 110}),           # 숫자 아님
])
def test_bad_data_is_undetermined(body, garment):
    assert check_ease("상의", body, garment)["verdict"] == "UNDETERMINED"


# --- category: 상의만 ---
@pytest.mark.parametrize("cat", ["상의", "tops", "top", "TOP"])
def test_top_category_is_accepted(cat):
    assert check_ease(cat, BODY, {"chest_girth_cm": 110})["category"] == "top"


@pytest.mark.parametrize("cat", ["하의", "bottoms", "bottom"])
def test_bottom_category_is_rejected(cat):
    with pytest.raises(ValueError, match="하의는 판정하지 않습니다"):
        check_ease(cat, BODY, {"chest_girth_cm": 110})


def test_unknown_category_raises():
    with pytest.raises(ValueError):
        check_ease("아우터", BODY, {"chest_girth_cm": 110})


# --- ML 응답 ---
def test_ml_response_keeps_only_chest_girth():
    assert body_from_ml_response(ML_RESPONSE) == {"chest_girth_cm": 100.08}   # 몸 너비·하체 키는 버림


def test_ml_response_without_male_wrapper():
    assert body_from_ml_response(ML_RESPONSE["male"])["chest_girth_cm"] == 100.08


def test_ml_response_missing_chest_is_undetermined():
    body = body_from_ml_response({"male": {"chest_width_cm": 34.9}})   # 몸 너비만 있고 둘레 없음
    assert check_ease("상의", body, {"chest_girth_cm": 110})["verdict"] == "UNDETERMINED"


# --- DB 행 (3D 의류 API와 같은 garment.measures) ---
def test_db_width_is_doubled_and_kr_only():
    sizes = sizes_from_db_rows(UNIQLO_ROWS)
    assert sizes[1] == {"size_label": "M", "chest_girth_cm": 106.0}         # KR M 53 × 2, US M(56) 제외
    assert [s["size_label"] for s in sizes] == ["S", "M", "L", "XL", "XXL"]


def test_db_rows_skip_body_basis_and_other_codes():
    rows = [{"size_label": "M", "measure_code": "chest_width", "basis": "garment", "value_cm": 53.0},
            {"size_label": "M", "measure_code": "body_length", "basis": "garment", "value_cm": 70.0},
            {"size_label": "M", "measure_code": "chest_girth", "basis": "body", "low_cm": 92, "high_cm": 98},
            {"size_label": "XL", "measure_code": "body_length", "basis": "garment", "value_cm": 74.0}]
    assert sizes_from_db_rows(rows) == [{"size_label": "M", "chest_girth_cm": 106.0}, {"size_label": "XL"}]


def test_db_row_without_basis_key():
    # 3D 의류 API(garments.py) 조회 결과에는 basis 열이 없을 수 있음 (JOIN 조건에서 이미 거름)
    rows = [{"item_code": "E422992-000", "category": "상의", "region": "KR", "size_label": "M",
             "measure_code": "chest_width", "value_cm": 53.0}]
    assert sizes_from_db_rows(rows) == [{"size_label": "M", "chest_girth_cm": 106.0}]


def test_measures_sql_matches_3d_api_tables():
    sql = MEASURES_SQL.lower()
    for part in ("garment.garments", "garment.sizes", "garment.measures",
                 "basis = 'garment'", "item_code = ?", "chest_width"):
        assert part in sql


# --- 전체 사이즈 판정·추천 ---
def test_uniqlo_end_to_end():
    body = body_from_ml_response(ML_RESPONSE)                        # 가슴 100.08
    r = check_all_sizes(UNIQLO_ROWS[0]["category"], body, sizes_from_db_rows(UNIQLO_ROWS), "M")
    assert r["selected"]["verdict"] == "FIT"                         # 106 - 100.08 = +5.9
    verdicts = {s["size_label"]: s["verdict"] for s in r["all_sizes"]}
    assert verdicts == {"S": "NO_FIT", "M": "FIT", "L": "FIT", "XL": "FIT", "XXL": "NO_FIT"}
    # S: 100 - 100.08 = -0.1 (작음) / XXL: 128 - 100.08 = +27.9 (너무 큼)
    assert r["fit_sizes"] == ["M", "L", "XL"] and r["recommended_size"] == "M"


def test_no_fit_size_gives_no_recommendation():
    r = check_all_sizes("상의", {"chest_girth_cm": 150.0}, [{"size_label": "M", "chest_girth_cm": 106.0}])
    assert r["fit_sizes"] == [] and r["recommended_size"] is None


def test_unknown_size_raises():
    with pytest.raises(ValueError):
        check_all_sizes("상의", BODY, [{"size_label": "M", "chest_girth_cm": 106}], "XXXL")
