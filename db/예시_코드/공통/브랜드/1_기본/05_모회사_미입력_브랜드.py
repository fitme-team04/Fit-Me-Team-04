# 목적: 모회사(group_name)가 비어 있는 브랜드 — 자료 정리 때 "모회사를 아직 안 채운 브랜드" 찾기
# 누가 쓰나: 공통 (3D / AI / 프론트. 관리자 자료 점검)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + WHERE IS NULL (NULL 은 = 로 비교 못 함)
# 출력: 표 2개 — 모회사 미입력 브랜드 1행(COVERNAT), 모회사 입력된 브랜드 3행(brand_id·이름·group_name)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/05_모회사_미입력_브랜드.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: group_name 이 NULL 인 브랜드 (WHERE group_name = NULL 은 늘 0행이라 IS NULL 을 씀)
def brands_without_group():
    sql = """
        SELECT b.brand_id, b.brand_name, b.country, b.group_name
        FROM garment.brands AS b
        WHERE b.group_name IS NULL
        ORDER BY b.brand_id
    """
    return query(sql)


# 목적: 반대로 모회사가 채워진 브랜드 (IS NOT NULL)
def brands_with_group():
    sql = """
        SELECT b.brand_id, b.brand_name, b.group_name
        FROM garment.brands AS b
        WHERE b.group_name IS NOT NULL
        ORDER BY b.brand_id
    """
    return query(sql)


if __name__ == "__main__":
    show("모회사 미입력 브랜드 (group_name IS NULL)", brands_without_group())
    show("모회사 입력된 브랜드 (group_name IS NOT NULL)", brands_with_group())
