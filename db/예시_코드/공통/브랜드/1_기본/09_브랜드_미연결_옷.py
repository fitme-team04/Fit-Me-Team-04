# 목적: 브랜드가 연결되지 않은 옷(brand_id 가 NULL) — 브랜드를 알 수 없는 수집 자료(예: kobo 공개 데이터)를 골라 브랜드 연결 작업 대상으로
# 누가 쓰나: 공통 (3D / AI / 프론트. 자료 적재 담당 점검)
# 난이도: 기본 — 표 1개(garment.garments) SELECT + WHERE brand_id IS NULL + ORDER BY
# 출력: 표 2개 — 브랜드 미연결 옷 1행(garment_id 13 mens-tops·출처·대상 성별), 미연결 옷 개수 1행(1)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/09_브랜드_미연결_옷.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: brand_id 가 비어 있는 옷 목록
def garments_without_brand():
    sql = """
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name, g.target_gender
        FROM garment.garments AS g
        WHERE g.brand_id IS NULL
        ORDER BY g.garment_id
    """
    return query(sql)


# 목적: 브랜드 미연결 옷 개수
def garments_without_brand_tally():
    sql = """
        SELECT COUNT(*) AS no_brand_tally
        FROM garment.garments AS g
        WHERE g.brand_id IS NULL
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드 미연결 옷 (brand_id IS NULL)", garments_without_brand())
    show("브랜드 미연결 옷 개수", garments_without_brand_tally())
