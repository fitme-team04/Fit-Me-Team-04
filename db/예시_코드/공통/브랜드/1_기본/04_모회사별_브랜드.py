# 목적: 모회사(group_name) 하나에 속한 브랜드 — 예: Fast Retailing 계열(UNIQLO, GU)은 사이즈 체계가 비슷한지 같이 볼 때
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + WHERE = + ORDER BY
# 출력: 표 2개 — Fast Retailing 계열 2행(GU·UNIQLO), Musinsa 계열 1행(brand_id·이름·나라)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/04_모회사별_브랜드.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 모회사 이름 → 그 계열 브랜드 목록
def brands_by_group(group_name="Fast Retailing"):
    sql = """
        SELECT b.brand_id, b.brand_name, b.country
        FROM garment.brands AS b
        WHERE b.group_name = %s
        ORDER BY b.brand_name
    """
    return query(sql, (group_name,))


if __name__ == "__main__":
    show("Fast Retailing 계열 브랜드", brands_by_group("Fast Retailing"))
    show("Musinsa 계열 브랜드", brands_by_group("Musinsa"))
