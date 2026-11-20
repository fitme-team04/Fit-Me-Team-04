# 목적: 옷을 고른 뒤 세 번째 드롭다운 — 사이즈 표기 체계(region) 탭과 사이즈 선택값 (value = size_id)
# 누가 쓰나: 프론트 (사이즈별 치수 비교는 공통/옷)
# 난이도: 기본 — 표 1개(garment.sizes) SELECT DISTINCT / WHERE(garment_id, region) + ORDER BY
# 출력: 옷별 표기 체계 탭과 사이즈 드롭다운: garment 6 의 KR 8행·US 3행, garment 13 의 US 3행
# 실행: .venv/bin/python db/예시_코드/front/1_기본/10_옷별_사이즈_선택목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 옷 한 벌에 있는 사이즈 표기 체계 목록 (KR / US ... 탭 이름)
def region_tabs(garment_id):
    sql = """
        SELECT DISTINCT s.region
        FROM garment.sizes AS s
        WHERE s.garment_id = %s
        ORDER BY s.region
    """
    tabs = []
    for row in query(sql, (garment_id,)):
        tabs.append(row["region"])
    return tabs


# 목적: 옷 한 벌 + 표기 체계 하나의 사이즈 드롭다운. size_id 순서 = 출처에 적힌 작은 → 큰 순서
def size_options(garment_id, region):
    sql = """
        SELECT s.size_id, s.size_label
        FROM garment.sizes AS s
        WHERE s.garment_id = %s
          AND s.region = %s
        ORDER BY s.size_id
    """
    options = []
    for row in query(sql, (garment_id, region)):
        options.append({"value": row["size_id"], "label": row["size_label"] + " (" + region + ")"})
    return options


if __name__ == "__main__":
    # garment_id 6 = UNIQLO 크루넥T(E422992-000, unisex), 13 = kobo mens-tops (db/sample/sample_data.sql)
    for garment_id in [6, 13]:
        tabs = region_tabs(garment_id)
        print()
        print("■ garment_id = " + str(garment_id) + " 의 표기 체계 탭: " + ", ".join(tabs))
        for region in tabs:
            show("사이즈 드롭다운 (garment_id = " + str(garment_id) + ", region = " + region + ")",
                 size_options(garment_id, region))
