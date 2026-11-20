# 목적: 치수 하나가 전체 평균보다 큰(넉넉한) 사이즈 찾기 + 치수가 있는 옷만 고르기 — 하위 질의(subquery) 연습
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 3개 JOIN + 단순 하위 질의 2종(값 하나를 돌려주는 (SELECT AVG ...), 목록을 돌려주는 IN (SELECT ...))
# 출력: 가슴단면 평균 초과 사이즈 2행, 어깨너비(옷) 평균 초과 2행(value_cm·avg_cm), 치수가 등록된 옷 3행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/10_평균보다_넓은_가슴단면.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 실측 치수 하나가 그 치수 전체 평균보다 큰 사이즈 + 평균과의 차이
def sizes_above_average(measure_code="chest_width"):
    sql = """
        SELECT g.item_code, g.garment_name, s.size_label, s.region, gm.value_cm,
               (SELECT ROUND(AVG(a.value_cm), 1)
                FROM garment.measures AS a
                WHERE a.measure_code = %s AND a.basis = 'garment') AS avg_cm
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE gm.measure_code = %s
          AND gm.basis = 'garment'
          AND gm.value_cm > (SELECT AVG(b.value_cm)
                             FROM garment.measures AS b
                             WHERE b.measure_code = %s AND b.basis = 'garment')
        ORDER BY gm.value_cm DESC
    """
    return query(sql, (measure_code, measure_code, measure_code))


# 목적: 치수가 하나라도 등록된 사이즈를 가진 옷만 (IN 하위 질의)
def garments_having_measures():
    sql = """
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name
        FROM garment.garments AS g
        WHERE g.garment_id IN (SELECT s.garment_id
                               FROM garment.sizes AS s
                               JOIN garment.measures AS gm ON gm.size_id = s.size_id)
        ORDER BY g.garment_id
    """
    return query(sql)


if __name__ == "__main__":
    show("가슴단면이 평균보다 큰 사이즈", sizes_above_average("chest_width"))
    show("어깨너비(옷)가 평균보다 큰 사이즈", sizes_above_average("garment_shoulder_width"))
    show("치수가 등록된 옷", garments_having_measures())
