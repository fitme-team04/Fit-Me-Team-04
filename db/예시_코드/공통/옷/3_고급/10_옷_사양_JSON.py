# 목적: 옷 한 벌의 사양(옷 정보 → 사이즈 목록 → 사이즈별 치수 목록)을 SQL 한 번으로 중첩 JSON 하나로 만들기 (API 응답·파일 저장용)
# 누가 쓰나: 공통 (프론트 API 응답, 3D 옷 모델 입력, AI 데이터 내보내기)
# 난이도: 고급 — 파생 테이블 2단 중첩 + 4개 표 LEFT JOIN + JSON_OBJECT·JSON_ARRAYAGG 집계 (파이썬에서 묶는 판은 3d/2_심화/07_옷_사이즈별_치수_JSON.py)
# 출력: COVERNAT 1848166 사양 JSON(옷 정보+sizes 6개·치수 배열, 화면만·파일 저장 없음), JSON 요약 6행·크루넥T 11행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/10_옷_사양_JSON.py
# 안쪽부터: 사이즈마다 치수 배열(m) → 옷마다 사이즈 배열(sz) → 옷 객체 하나. JSON_ARRAYAGG 는 배열 안 순서를 보장하지 않음
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷(출처 + 상품번호) 하나의 사양 JSON 글자 (없으면 None)
def garment_spec_json(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT JSON_OBJECT(
                   'source_name',   g.source_name,
                   'item_code',     g.item_code,
                   'garment_name',  g.garment_name,
                   'category',      g.category,
                   'target_gender', g.target_gender,
                   'fit',           g.fit,
                   'sizes',         COALESCE(sz.sizes, JSON_ARRAY())
               ) AS spec
        FROM garment.garments AS g
        LEFT JOIN (
            SELECT s.garment_id,
                   JSON_ARRAYAGG(JSON_OBJECT(
                       'size_label', s.size_label,
                       'region',     s.region,
                       'measures',   COALESCE(m.measures, JSON_ARRAY())
                   )) AS sizes
            FROM garment.sizes AS s
            LEFT JOIN (
                SELECT gm.size_id,
                       JSON_ARRAYAGG(JSON_OBJECT(
                           'measure_code', gm.measure_code,
                           'korean_name',  d.korean_name,
                           'basis',        gm.basis,
                           'value_cm',     gm.value_cm,
                           'low_cm',       gm.low_cm,
                           'high_cm',      gm.high_cm
                       )) AS measures
                FROM garment.measures AS gm
                JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
                GROUP BY gm.size_id
            ) AS m ON m.size_id = s.size_id
            GROUP BY s.garment_id
        ) AS sz ON sz.garment_id = g.garment_id
        WHERE g.source_name = %s
          AND g.item_code = %s
    """
    rows = query(sql, (source_name, item_code))
    if len(rows) == 0:
        return None
    return rows[0]["spec"]


# 목적: JSON 글자 → 사이즈마다 (표기, 지역, 치수 수) 요약 행 (파이썬 dict 로 풀어서 확인)
def spec_summary(spec_text):
    spec = json.loads(spec_text)
    rows = []
    for size in spec["sizes"]:
        rows.append({
            "item_code": spec["item_code"],
            "size_label": size["size_label"],
            "region": size["region"],
            "measure_tally": len(size["measures"]),
        })
    return rows


if __name__ == "__main__":
    text = garment_spec_json("musinsa_ml_project", "1848166")
    print()
    print("■ COVERNAT 1848166 사양 JSON")
    print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
    show("COVERNAT 1848166 JSON 요약", spec_summary(text))
    show("크루넥T(E422992-000) JSON 요약", spec_summary(garment_spec_json("uniqlo_site", "E422992-000")))
