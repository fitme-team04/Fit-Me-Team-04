# 목적: 내 신체 치수(dict)로 옷 한 벌의 사이즈 순위 매기기 — 여유분(ease) = 옷 치수 × factor − 신체 치수 (ref.measure_maps), SQL 만으로
# 누가 쓰나: 공통 (AI 규칙 추천 기준과 같은 규칙을 SQL 로 확인, 프론트 추천 화면, 3D 여유 표시)
# 난이도: 고급 — dict 파생 테이블 CTE + 5개 표 JOIN(옷·사이즈·치수·measure_maps·신체) + 여유분 계산식 + 2단 CTE 집계 + 창 함수 RANK()
# 출력: 크루넥T 여유분 상세 4행(신체·옷 cm·factor·ease_cm), 크루넥T 사이즈 순위 2행(verdict), COVERNAT 순위 1행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/09_신체치수로_사이즈_순위.py
# 규칙(_추천.py 와 같은 뜻): 모든 항목 여유분 ≥ 0 이면 fit, 하나라도 음수면 small. 순위는 fit 먼저, 그 안에서 평균 여유분이 작은 순
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: {measure_code: cm} → ("SELECT %s AS measure_code, %s AS value_cm UNION ALL ...", [값...])
def body_table_sql(body):
    parts = []
    params = []
    for code in body:
        if len(parts) == 0:
            parts.append("SELECT %s AS measure_code, %s AS value_cm")
        else:
            parts.append("SELECT %s, %s")
        params.append(code)
        params.append(body[code])
    return " UNION ALL ".join(parts), params


# 목적: 사이즈 × 대응 항목마다 여유분 (예: 가슴단면 53 × 2 − 가슴둘레 94.1 = 11.9 cm)
def ease_detail(body, source_name="uniqlo_site", item_code="E422992-000"):
    body_sql, params = body_table_sql(body)
    sql = """
        WITH body_input AS (""" + body_sql + """)
        SELECT s.size_label, s.region, mm.body_measure_code, gm.measure_code AS garment_measure_code,
               b.value_cm AS body_cm, gm.value_cm AS garment_cm, mm.factor,
               ROUND(gm.value_cm * mm.factor - b.value_cm, 1) AS ease_cm
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'garment'
        JOIN ref.measure_maps AS mm ON mm.garment_measure_code = gm.measure_code
        JOIN body_input AS b ON b.measure_code = mm.body_measure_code
        WHERE g.source_name = %s
          AND g.item_code = %s
        ORDER BY s.region, s.size_id, mm.body_measure_code
    """
    params.append(source_name)
    params.append(item_code)
    return query(sql, tuple(params))


# 목적: 사이즈마다 비교 항목 수·최소/평균 여유분·판정(fit/small) + 순위
def size_ranking(body, source_name="uniqlo_site", item_code="E422992-000"):
    body_sql, params = body_table_sql(body)
    sql = """
        WITH body_input AS (""" + body_sql + """),
        ease_rows AS (
            SELECT s.size_id, s.size_label, s.region,
                   gm.value_cm * mm.factor - b.value_cm AS ease_cm
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'garment'
            JOIN ref.measure_maps AS mm ON mm.garment_measure_code = gm.measure_code
            JOIN body_input AS b ON b.measure_code = mm.body_measure_code
            WHERE g.source_name = %s
              AND g.item_code = %s
        ),
        per_size AS (
            SELECT e.size_id, e.size_label, e.region,
                   COUNT(*) AS compared,
                   ROUND(MIN(e.ease_cm), 1) AS min_ease_cm,
                   ROUND(AVG(e.ease_cm), 1) AS avg_ease_cm,
                   CASE WHEN MIN(e.ease_cm) >= 0 THEN 'fit' ELSE 'small' END AS verdict
            FROM ease_rows AS e
            GROUP BY e.size_id, e.size_label, e.region
        )
        SELECT RANK() OVER (ORDER BY CASE WHEN p.verdict = 'fit' THEN 0 ELSE 1 END, p.avg_ease_cm) AS size_rank,
               p.size_label, p.region, p.compared, p.min_ease_cm, p.avg_ease_cm, p.verdict
        FROM per_size AS p
        ORDER BY size_rank, p.size_id
    """
    params.append(source_name)
    params.append(item_code)
    return query(sql, tuple(params))


if __name__ == "__main__":
    # 예시 신체: body.measures profile_id 18 의 가슴둘레·어깨너비
    my_body = {"chest_girth": 94.1, "shoulder_width": 42.9}
    show("크루넥T(E422992-000) 여유분 상세", ease_detail(my_body, "uniqlo_site", "E422992-000"))
    show("크루넥T(E422992-000) 사이즈 순위", size_ranking(my_body, "uniqlo_site", "E422992-000"))
    # 팔길이까지 넣으면 반팔(소매 21.5 cm)은 여유분이 음수 → small
    arm_body = {"chest_girth": 94.1, "shoulder_width": 42.9, "arm_length": 56.3}
    show("COVERNAT(1848166) 사이즈 순위 — 팔길이 포함", size_ranking(arm_body, "musinsa_ml_project", "1848166"))
