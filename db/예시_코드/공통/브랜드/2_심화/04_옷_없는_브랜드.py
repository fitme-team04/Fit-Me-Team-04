# 목적: 등록은 됐지만 옷이 한 벌도 없는 브랜드 — 다음에 수집할 브랜드 목록 (예: GU, MUSINSA STANDARD)
# 누가 쓰나: 공통 (3D / AI / 프론트. 자료 수집 계획)
# 난이도: 심화 — 2개 표 LEFT JOIN(브랜드 + 옷) 후 WHERE 오른쪽 키 IS NULL (짝이 없는 행만 남기기)
# 출력: 표 1개 — 옷이 한 벌도 없는 브랜드 2행(GU·MUSINSA STANDARD, 열 brand_id·이름·나라·모회사)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/04_옷_없는_브랜드.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷이 없는 브랜드. LEFT JOIN 은 짝이 없으면 옷 쪽 열을 NULL 로 채우므로 그 NULL 만 고름
def brands_without_garments():
    sql = """
        SELECT b.brand_id, b.brand_name, b.country, b.group_name
        FROM garment.brands AS b
        LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
        WHERE g.garment_id IS NULL
        ORDER BY b.brand_id
    """
    return query(sql)


if __name__ == "__main__":
    show("옷이 한 벌도 없는 브랜드", brands_without_garments())
