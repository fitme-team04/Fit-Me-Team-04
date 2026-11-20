# 목적: 옷마다 사이즈 중 몇 %에 치수가 채워졌는지(옷 실측·권장 범위 따로) + 치수가 전혀 없는 옷 — 수집 진척 점검
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 고급 — CTE(WITH) 안에서 EXISTS (상관 하위 질의)로 사이즈마다 0/1 표시 → 바깥에서 비율 계산, NOT EXISTS 로 없는 옷 고르기
# 출력: 옷마다 치수 채움률 3행(옷 실측·권장 범위 채움 %), 치수가 전혀 없는 uniqlo_site 옷 11행(has_sizes)
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/04_치수_채움률_EXISTS.py
# EXISTS (SELECT 1 ...) = 하위 질의가 1행이라도 있으면 1(참), 없으면 0(거짓). 개수가 아니라 "있나 없나"만 볼 때 씀
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷마다 사이즈 수, 옷 실측이 있는 사이즈 수·비율, 권장 범위가 있는 사이즈 수·비율
def fill_rate_by_garment():
    sql = """
        WITH size_flags AS (
            SELECT s.garment_id, s.size_id,
                   EXISTS (SELECT 1 FROM garment.measures AS gm
                           WHERE gm.size_id = s.size_id AND gm.basis = 'garment') AS has_garment,
                   EXISTS (SELECT 1 FROM garment.measures AS gm
                           WHERE gm.size_id = s.size_id AND gm.basis = 'body') AS has_body
            FROM garment.sizes AS s
        )
        SELECT g.garment_id, g.item_code, g.garment_name,
               COUNT(*) AS size_tally,
               SUM(f.has_garment) AS sizes_with_garment,
               ROUND(SUM(f.has_garment) * 100 / COUNT(*), 1) AS garment_fill_pct,
               SUM(f.has_body) AS sizes_with_body,
               ROUND(SUM(f.has_body) * 100 / COUNT(*), 1) AS body_fill_pct
        FROM garment.garments AS g
        JOIN size_flags AS f ON f.garment_id = g.garment_id
        GROUP BY g.garment_id, g.item_code, g.garment_name
        ORDER BY garment_fill_pct DESC, g.garment_id
    """
    return query(sql)


# 목적: 치수가 한 행도 없는 옷 (사이즈가 없거나, 사이즈는 있어도 치수가 없음) — 출처 하나만
def garments_without_any_measure(source_name="uniqlo_site"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name,
               EXISTS (SELECT 1 FROM garment.sizes AS s2
                       WHERE s2.garment_id = g.garment_id) AS has_sizes
        FROM garment.garments AS g
        WHERE g.source_name = %s
          AND NOT EXISTS (SELECT 1
                          FROM garment.sizes AS s
                          JOIN garment.measures AS gm ON gm.size_id = s.size_id
                          WHERE s.garment_id = g.garment_id)
        ORDER BY g.garment_id
    """
    return query(sql, (source_name,))


if __name__ == "__main__":
    show("옷마다 치수 채움률", fill_rate_by_garment())
    show("치수가 전혀 없는 uniqlo_site 옷", garments_without_any_measure("uniqlo_site"))
