# 목적: 치수가 n개 이상 등록된 사이즈만 고르기 — 3D 옷 모델·추천에 쓸 만큼 자료가 찬 사이즈
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 3개 JOIN(garments + sizes + measures) + GROUP BY + HAVING (묶은 뒤 거르기)
# 출력: 옷 실측 치수 4개 이상 사이즈 3행, 2개 이상 4행(옷·표기·지역·치수 수), 가슴단면 있는 옷 3행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/08_치수많은_사이즈_HAVING.py
# WHERE 는 묶기 전 행을, HAVING 은 묶은 뒤 그룹(COUNT 결과)을 거름
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 실측(basis = garment) 치수가 min_tally 개 이상인 사이즈
def sizes_with_enough_measures(min_tally=4):
    sql = """
        SELECT g.garment_id, g.item_code, s.size_label, s.region,
               COUNT(*) AS garment_measure_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE gm.basis = 'garment'
        GROUP BY g.garment_id, g.item_code, s.size_id, s.size_label, s.region
        HAVING COUNT(*) >= %s
        ORDER BY garment_measure_tally DESC, g.garment_id, s.size_id
    """
    return query(sql, (min_tally,))


# 목적: 치수 항목 하나(measure_code)가 등록된 사이즈 수가 min_sizes 개 이상인 옷
def garments_with_measure(measure_code="chest_width", min_sizes=1):
    sql = """
        SELECT g.garment_id, g.item_code, COUNT(*) AS size_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE gm.measure_code = %s
        GROUP BY g.garment_id, g.item_code
        HAVING COUNT(*) >= %s
        ORDER BY size_tally DESC, g.garment_id
    """
    return query(sql, (measure_code, min_sizes))


if __name__ == "__main__":
    show("옷 실측 치수 4개 이상인 사이즈", sizes_with_enough_measures(4))
    show("옷 실측 치수 2개 이상인 사이즈", sizes_with_enough_measures(2))
    show("가슴단면이 1개 사이즈 이상 있는 옷", garments_with_measure("chest_width", 1))
