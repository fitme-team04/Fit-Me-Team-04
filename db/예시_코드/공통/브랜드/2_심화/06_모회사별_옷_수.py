# 목적: 모회사(group_name)마다 거느린 브랜드 이름과 옷 수 — 모회사가 없는 브랜드는 '(독립)' 으로 한 묶음
# 누가 쓰나: 공통 (3D / AI / 프론트. 계열사 단위 사이즈 체계 비교 준비)
# 난이도: 심화 — 2개 표 LEFT JOIN + GROUP BY COALESCE(...) + GROUP_CONCAT(브랜드 이름 이어 붙이기)
# 출력: 표 1개 — 모회사별 3행(group_name·brand_names·brand_tally·garment_tally), 모회사 없는 COVERNAT은 '(독립)'
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/06_모회사별_옷_수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 모회사별 브랜드 이름 목록·브랜드 수·옷 수
def tally_by_group():
    sql = """
        SELECT COALESCE(b.group_name, '(독립)')                               AS group_name,
               GROUP_CONCAT(DISTINCT b.brand_name ORDER BY b.brand_name SEPARATOR ', ') AS brand_names,
               COUNT(DISTINCT b.brand_id)                                     AS brand_tally,
               COUNT(g.garment_id)                                            AS garment_tally
        FROM garment.brands AS b
        LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
        GROUP BY COALESCE(b.group_name, '(독립)')
        ORDER BY garment_tally DESC
    """
    return query(sql)


if __name__ == "__main__":
    show("모회사별 브랜드·옷 수", tally_by_group())
