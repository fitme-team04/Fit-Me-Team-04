# 목적: 한 사람의 몸 치수를 옷 사이즈별 권장 신체 범위(basis = body)에 대 보기 → 3D 드레이프(옷 입히기) 전에 맞음·끼임·헐렁 판정
# 누가 쓰나: 3D
# 난이도: 고급 — 5개 표 JOIN(옷·사이즈·치수·정의 + 몸 치수 LEFT JOIN) + CASE 판정 + 조건부 SUM 집계로 사이즈별 요약
# 출력: profile 18·22 × UNIQLO E422992-000 드레이프 판정 표(각 4행; body_cm·drape·off_center_cm) + 사이즈별 요약(각 2행)
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/07_옷_몸범위_드레이프_매칭.py
# 판정: fit = 범위 안 / tight = 몸이 범위보다 큼(끼임) / loose = 몸이 범위보다 작음(헐렁) / no_body = 몸 치수 없음
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 두 함수가 같이 쓰는 FROM ~ WHERE (몸 치수는 LEFT JOIN: 없는 치수도 no_body 로 보이게)
MATCH_FROM = """
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'body'
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        LEFT JOIN body.measures AS bm ON bm.measure_code = gm.measure_code AND bm.profile_id = %s
        WHERE g.source_name = %s AND g.item_code = %s
"""

DRAPE_CASE = """
        CASE WHEN bm.value_cm IS NULL THEN 'no_body'
             WHEN bm.value_cm > gm.high_cm THEN 'tight'
             WHEN bm.value_cm < gm.low_cm THEN 'loose'
             ELSE 'fit' END
"""


# 목적: 사이즈 × 치수마다 범위·몸 값·판정·범위 가운데와 차이
def drape_rows(profile_id, source_name, item_code):
    sql = """
        SELECT s.size_label, s.region, gm.measure_code, d.korean_name,
               gm.low_cm, gm.high_cm, bm.value_cm AS body_cm,
               """ + DRAPE_CASE + """ AS drape,
               ROUND(bm.value_cm - (gm.low_cm + gm.high_cm) / 2, 1) AS off_center_cm
    """ + MATCH_FROM + """
        ORDER BY s.region, s.size_id, gm.measure_code
    """
    return query(sql, (profile_id, source_name, item_code))


# 목적: 사이즈마다 판정 개수 (fit 이 많고 tight 가 적은 사이즈가 드레이프 1순위)
def drape_summary(profile_id, source_name, item_code):
    sql = """
        SELECT s.size_label, s.region,
               SUM(CASE WHEN """ + DRAPE_CASE + """ = 'fit'   THEN 1 ELSE 0 END) AS fit_tally,
               SUM(CASE WHEN """ + DRAPE_CASE + """ = 'tight' THEN 1 ELSE 0 END) AS tight_tally,
               SUM(CASE WHEN """ + DRAPE_CASE + """ = 'loose' THEN 1 ELSE 0 END) AS loose_tally,
               COUNT(*) AS range_tally
    """ + MATCH_FROM + """
        GROUP BY s.size_id, s.size_label, s.region
        ORDER BY fit_tally DESC, tight_tally, s.size_id
    """
    return query(sql, (profile_id, source_name, item_code))


if __name__ == "__main__":
    # UNIQLO 크루넥T (E422992-000): KR M · US M 에 가슴·허리 권장 범위
    show("드레이프 판정 (profile 18 × UNIQLO E422992-000)", drape_rows(18, "uniqlo_site", "E422992-000"))
    show("사이즈별 요약 (profile 18)", drape_summary(18, "uniqlo_site", "E422992-000"))
    show("드레이프 판정 (profile 22 × UNIQLO E422992-000)", drape_rows(22, "uniqlo_site", "E422992-000"))
    show("사이즈별 요약 (profile 22)", drape_summary(22, "uniqlo_site", "E422992-000"))
