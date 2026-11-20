# 목적: 옷마다 지역(KR / US ...)별로 사이즈가 몇 개이고 어떤 표기인지 한 줄로 — 어느 옷이 어느 표기 체계를 갖췄는지
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 2개 JOIN(garments + sizes) + GROUP BY 2열 + COUNT·GROUP_CONCAT
# 출력: (옷, 지역)별 사이즈 수·표기 목록(size_labels) 4행, 지역별 옷 수·사이즈 수 2행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/02_옷별_지역별_사이즈수.py
# GROUP_CONCAT(값 ORDER BY 순서 SEPARATOR ',') = 그룹 안의 값을 글자 하나로 이어 붙임
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (옷, 지역)마다 사이즈 개수 + 표기 목록
def size_labels_by_garment_region():
    sql = """
        SELECT g.garment_id, g.item_code, s.region,
               COUNT(*) AS size_tally,
               GROUP_CONCAT(s.size_label ORDER BY s.size_id SEPARATOR ',') AS size_labels
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        GROUP BY g.garment_id, g.item_code, s.region
        ORDER BY g.garment_id, s.region
    """
    return query(sql)


# 목적: 지역마다 그 표기를 가진 옷이 몇 벌인지
def garment_tally_by_region():
    sql = """
        SELECT s.region,
               COUNT(DISTINCT g.garment_id) AS garment_tally,
               COUNT(*) AS size_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        GROUP BY s.region
        ORDER BY s.region
    """
    return query(sql)


if __name__ == "__main__":
    show("(옷, 지역)별 사이즈 수·표기", size_labels_by_garment_region())
    show("지역별 옷 수·사이즈 수", garment_tally_by_region())
