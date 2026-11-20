# 목적: 옷 한 벌의 사이즈 하나 → 천 시뮬레이션(cloth simulation) 입력 JSON: 패턴 실측 + 몸 기준 둘레 환산 + 권장 범위 + 몸과의 둘레 여유분
# 누가 쓰나: 3D
# 난이도: 고급 — 6개 표(옷·브랜드·사이즈·옷 치수·대응 규칙·몸 치수) + SQL 안 JSON 조립(JSON_OBJECT·JSON_OBJECTAGG·JSON_ARRAY) 상관 서브쿼리 4개
# 출력: 옷 2벌 M/KR 천 시뮬 치수 표(8·6행) + JSON(panel_cm·body_range_cm·ease_cm 등); --save 면 out/3d/cloth_*.json
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/09_천시뮬_옷치수_JSON.py            (JSON 은 화면에 출력)
#       .venv/bin/python db/예시_코드/3d/3_고급/09_천시뮬_옷치수_JSON.py --save     (out/3d/cloth_<source>_<item>_<size>_<region>.json 으로도 저장)
# 2_심화/07_옷_사이즈별_치수_JSON.py 는 사이즈 전부를 파이썬으로 묶음. 여기는 사이즈 하나를 SQL 이 바로 JSON 으로 만듦
# ease_cm(여유분) = 옷 둘레(단면 × 2) − 몸 둘레. factor 2 인 둘레 규칙만 (길이 규칙은 재는 법이 출처마다 달라 뺌)
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show, save_text

# MySQL 은 JSON 키를 자기 순서로 정렬함 → 화면·파일은 이 순서로 다시 놓음
KEY_ORDER = ["brand_name", "source_name", "item_code", "garment_name", "category", "target_gender", "fit",
             "size_label", "region", "unit", "panel_cm", "garment_girth_cm", "body_range_cm",
             "fit_profile_id", "ease_cm"]


# 목적: 사이즈 하나의 천 시뮬 JSON 을 SQL 로 만들어 dict 로 (없으면 None). profile_id 가 None 이면 ease_cm 은 null
def cloth_doc(source_name, item_code, size_label, region, profile_id=None):
    sql = """
        SELECT JSON_OBJECT(
            'brand_name', b.brand_name, 'source_name', g.source_name, 'item_code', g.item_code,
            'garment_name', g.garment_name, 'category', g.category,
            'target_gender', g.target_gender, 'fit', g.fit,
            'size_label', s.size_label, 'region', s.region, 'unit', 'cm',
            'panel_cm', (
                SELECT JSON_OBJECTAGG(gm.measure_code, gm.value_cm)
                FROM garment.measures AS gm
                WHERE gm.size_id = s.size_id AND gm.basis = 'garment'),
            'garment_girth_cm', (
                SELECT JSON_OBJECTAGG(mm.body_measure_code, ROUND(gm.value_cm * mm.factor, 1))
                FROM garment.measures AS gm
                JOIN ref.measure_maps AS mm ON mm.garment_measure_code = gm.measure_code
                WHERE gm.size_id = s.size_id AND gm.basis = 'garment' AND mm.factor = 2),
            'body_range_cm', (
                SELECT JSON_OBJECTAGG(gm.measure_code, JSON_ARRAY(gm.low_cm, gm.high_cm))
                FROM garment.measures AS gm
                WHERE gm.size_id = s.size_id AND gm.basis = 'body'),
            'fit_profile_id', %s,
            'ease_cm', (
                SELECT JSON_OBJECTAGG(mm.body_measure_code, ROUND(gm.value_cm * mm.factor - bm.value_cm, 1))
                FROM garment.measures AS gm
                JOIN ref.measure_maps AS mm ON mm.garment_measure_code = gm.measure_code
                JOIN body.measures AS bm ON bm.measure_code = mm.body_measure_code AND bm.profile_id = %s
                WHERE gm.size_id = s.size_id AND gm.basis = 'garment' AND mm.factor = 2)
        ) AS doc
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        WHERE g.source_name = %s AND g.item_code = %s AND s.size_label = %s AND s.region = %s
    """
    rows = query(sql, (profile_id, profile_id, source_name, item_code, size_label, region))
    if len(rows) == 0:
        return None
    raw = json.loads(rows[0]["doc"])
    ordered = {}
    for key in KEY_ORDER:
        ordered[key] = raw.get(key)
    return ordered


# 목적: JSON 안 치수 묶음을 표 행으로 펼치기 (화면 확인용)
def flat_rows(doc):
    rows = []
    for section in ["panel_cm", "garment_girth_cm", "body_range_cm", "ease_cm"]:
        values = doc[section]
        if values is None:
            continue
        for code in values:
            rows.append({"section": section, "measure_code": code, "value": values[code]})
    return rows


# 목적: 실행 예시 하나: 표 → JSON 출력 → (--save 면) 파일 저장
def demo(source_name, item_code, size_label, region, profile_id, save):
    title = source_name + " / " + item_code + " / " + size_label + " / " + region
    doc = cloth_doc(source_name, item_code, size_label, region, profile_id)
    if doc is None:
        print("  (" + title + " 사이즈 없음)")
        return
    show("천 시뮬 치수 (" + title + ", 몸 = profile " + str(profile_id) + ")", flat_rows(doc))
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    print()
    print("■ 천 시뮬 입력 JSON (" + title + ")")
    print(text)
    if save:
        name = "3d/cloth_" + source_name + "_" + item_code + "_" + size_label + "_" + region + ".json"
        path = save_text(name, text)
        print("  → 저장: " + str(path))


if __name__ == "__main__":
    save = "--save" in sys.argv
    # UNIQLO 크루넥T KR M: 실측 4개 + 권장 범위 2개, 몸 = profile 18 (가슴 94.1)
    demo("uniqlo_site", "E422992-000", "M", "KR", 18, save)
    # COVERNAT 티셔츠 KR M: 실측 4개 (권장 범위 없음 → body_range_cm null), 몸 = profile 20
    demo("musinsa_ml_project", "1848166", "M", "KR", 20, save)
