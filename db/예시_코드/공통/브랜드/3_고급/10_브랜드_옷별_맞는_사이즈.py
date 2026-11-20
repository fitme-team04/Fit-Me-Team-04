# 목적: 내 몸 치수(dict)를 넣으면 브랜드의 옷마다(지역별) 맞는 사이즈 중 가장 딱 맞는 것 하나 — "유니클로에서 나는 각 옷 몇 사이즈?"
# 누가 쓰나: 공통 (3D / AI / 프론트. 브랜드 화면 "내 사이즈" 표시, AI 규칙 추천과 같은 기준)
# 난이도: 고급 — CTE 4단(내 몸 → 여유분 → 사이즈 요약 → 순위) + 6개 표 JOIN(ref.measure_maps 여유분 계산식) + ROW_NUMBER() OVER (PARTITION BY ...)
# 출력: 내 몸 치수 dict 1줄 + 표 2개 — UNIQLO 옷별 맞는 사이즈 2행(KR·US 모두 M), COVERNAT 1행(best_size·min_ease_cm)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/10_브랜드_옷별_맞는_사이즈.py
# 규칙 (_추천.py · db/query/recommend/02_size_rank.sql 과 같음)
#  - 여유분(ease) = 옷 실측 × factor − 신체 치수 (ref.measure_maps, basis = garment)
#  - 모든 항목 여유분 ≥ 0 이면 fit, 하나라도 음수면 small
#  - 순위: fit 먼저, 그 안에서 평균 여유분이 작은 순 → 1위가 "맞는 것 중 가장 작은(딱 맞는) 사이즈"
# 내 몸 치수는 DB 에 없는 값이라 SELECT %s, CAST(%s ...) UNION ALL ... 로 질의 안에서 작은 표(my_body)를 만듦 (값은 %s 로만 넘김)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show

# 예시 몸 치수 (cm). 키는 ref.measure_maps 의 body_measure_code
DEFAULT_BODY = {
    "chest_girth": 94.0,
    "shoulder_width": 42.0,
}


# 목적: {코드: 값} → ("SELECT %s AS measure_code, CAST(%s AS DECIMAL(6,1)) AS value_cm UNION ALL ...", 값 목록)
# PyMySQL 은 파이썬 float 를 94.0e0(DOUBLE)로 보내므로 DECIMAL 로 바꿔 둠 → ROUND 가 _추천.py 처럼 .5 올림
def body_table_sql(body):
    parts = []
    params = []
    for code in body:
        if len(parts) == 0:
            parts.append("SELECT %s AS measure_code, CAST(%s AS DECIMAL(6,1)) AS value_cm")
        else:
            parts.append("SELECT %s, CAST(%s AS DECIMAL(6,1))")
        params.append(code)
        params.append(body[code])
    return " UNION ALL ".join(parts), params


# 목적: 브랜드 + 내 몸 → (옷, 지역)마다 1위 사이즈와 그 여유분 요약
def best_size_per_garment(brand_name="UNIQLO", body=None):
    if body is None:
        body = DEFAULT_BODY
    if len(body) == 0:
        return []
    body_sql, body_params = body_table_sql(body)
    sql = """
        WITH my_body AS (
            """ + body_sql + """
        ),
        ease AS (
            SELECT g.garment_id, g.item_code, g.garment_name, s.size_id, s.size_label, s.region,
                   mm.body_measure_code,
                   gm.value_cm * mm.factor - mb.value_cm AS ease_cm
            FROM garment.brands AS b
            JOIN garment.garments AS g ON g.brand_id = b.brand_id
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'garment'
            JOIN ref.measure_maps AS mm ON mm.garment_measure_code = gm.measure_code
            JOIN my_body AS mb ON mb.measure_code = mm.body_measure_code
            WHERE b.brand_name = %s
        ),
        per_size AS (
            SELECT e.garment_id, e.item_code, e.garment_name, e.size_id, e.size_label, e.region,
                   COUNT(*)              AS compared_tally,
                   ROUND(MIN(e.ease_cm), 1) AS min_ease_cm,
                   ROUND(AVG(e.ease_cm), 1) AS avg_ease_cm
            FROM ease AS e
            GROUP BY e.garment_id, e.item_code, e.garment_name, e.size_id, e.size_label, e.region
        ),
        ranked AS (
            SELECT p.*,
                   CASE WHEN p.min_ease_cm >= 0 THEN 'fit' ELSE 'small' END AS size_status,
                   ROW_NUMBER() OVER (PARTITION BY p.garment_id, p.region
                                      ORDER BY CASE WHEN p.min_ease_cm >= 0 THEN 0 ELSE 1 END,
                                               p.avg_ease_cm) AS rank_no,
                   COUNT(*) OVER (PARTITION BY p.garment_id, p.region) AS candidate_tally
            FROM per_size AS p
        )
        SELECT r.item_code, r.garment_name, r.region, r.size_label AS best_size,
               r.size_status, r.compared_tally, r.min_ease_cm, r.avg_ease_cm, r.candidate_tally
        FROM ranked AS r
        WHERE r.rank_no = 1
        ORDER BY r.garment_id, r.region
    """
    params = tuple(body_params) + (brand_name,)
    return query(sql, params)


if __name__ == "__main__":
    print("내 몸 치수:", DEFAULT_BODY)
    show("UNIQLO 옷별 맞는 사이즈 (여유분 규칙)", best_size_per_garment("UNIQLO", DEFAULT_BODY))
    show("COVERNAT 옷별 맞는 사이즈 (여유분 규칙)", best_size_per_garment("COVERNAT", DEFAULT_BODY))
