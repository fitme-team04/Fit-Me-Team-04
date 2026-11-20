# 목적: 내 신체 치수(파이썬 dict)가 옷 한 벌의 사이즈별 권장 신체 범위(basis = body, low~high) 안인지 항목마다 판정 + 사이즈별 맞음 비율
# 누가 쓰나: 공통 (프론트 "권장 체형" 안내, AI 규칙 추천의 참고 점수, 3D 확인)
# 난이도: 고급 — dict 를 UNION ALL 파생 테이블로 만들어 4개 표와 JOIN + CASE 판정 + CTE 위에서 비율 집계
# 출력: 크루넥T 권장 범위 판정 4행(신체·low·high·status), 사이즈별 범위 안 비율 2행, profile_id 19 신체로 2행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/08_권장범위_체크.py
# 파생 테이블: (SELECT 'chest_girth' AS measure_code, 94.1 AS value_cm UNION ALL SELECT 'waist_girth', 77.7) 처럼
#   SQL 안에서 잠깐 만드는 표. 값은 모두 %s 자리로 넘김 (SQL 글자에 직접 붙이지 않음)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: {measure_code: cm} → ("SELECT %s AS measure_code, %s AS value_cm UNION ALL SELECT %s, %s ...", [값...])
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


# 목적: 사이즈 × 항목마다 신체값이 범위 아래(below) / 안(in) / 위(above) 인지
def range_check(body, source_name="uniqlo_site", item_code="E422992-000"):
    body_sql, params = body_table_sql(body)
    sql = """
        SELECT s.size_label, s.region, gm.measure_code, d.korean_name,
               b.value_cm AS body_cm, gm.low_cm, gm.high_cm,
               CASE
                   WHEN b.value_cm < gm.low_cm  THEN 'below'
                   WHEN b.value_cm > gm.high_cm THEN 'above'
                   ELSE 'in'
               END AS status
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'body'
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        JOIN (""" + body_sql + """) AS b ON b.measure_code = gm.measure_code
        WHERE g.source_name = %s
          AND g.item_code = %s
        ORDER BY s.region, s.size_id, gm.measure_code
    """
    params.append(source_name)
    params.append(item_code)
    return query(sql, tuple(params))


# 목적: 사이즈마다 비교 항목 수 / 범위 안 항목 수 / 비율 (비율 높은 순)
def range_score_by_size(body, source_name="uniqlo_site", item_code="E422992-000"):
    body_sql, params = body_table_sql(body)
    sql = """
        WITH body_input AS (""" + body_sql + """),
        checks AS (
            SELECT s.size_id, s.size_label, s.region,
                   CASE WHEN b.value_cm BETWEEN gm.low_cm AND gm.high_cm THEN 1 ELSE 0 END AS in_range
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'body'
            JOIN body_input AS b ON b.measure_code = gm.measure_code
            WHERE g.source_name = %s
              AND g.item_code = %s
        )
        SELECT c.size_label, c.region,
               COUNT(*) AS compared,
               SUM(c.in_range) AS in_range_tally,
               ROUND(SUM(c.in_range) / COUNT(*), 2) AS in_range_ratio
        FROM checks AS c
        GROUP BY c.size_id, c.size_label, c.region
        ORDER BY in_range_ratio DESC, c.size_id
    """
    params.append(source_name)
    params.append(item_code)
    return query(sql, tuple(params))


if __name__ == "__main__":
    # 예시 신체: body.measures profile_id 18 의 가슴둘레·허리둘레
    my_body = {"chest_girth": 94.1, "waist_girth": 77.7}
    show("크루넥T(E422992-000) 권장 범위 판정 — 가슴 94.1 / 허리 77.7", range_check(my_body, "uniqlo_site", "E422992-000"))
    show("크루넥T(E422992-000) 사이즈별 범위 안 비율", range_score_by_size(my_body, "uniqlo_site", "E422992-000"))
    big_body = {"chest_girth": 100.7, "waist_girth": 95.8}
    show("같은 옷, 가슴 100.7 / 허리 95.8 (profile_id 19)", range_score_by_size(big_body, "uniqlo_site", "E422992-000"))
