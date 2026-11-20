# 목적: 브랜드 하나(brand_id)의 옷이 어느 출처에서 왔고 어떤 종류·대상 성별이 있는지 (중복 없이) — 브랜드 자료 범위 파악
# 누가 쓰나: 공통 (3D / AI / 프론트. AI 학습 자료 출처 확인)
# 난이도: 기본 — 표 1개(garment.garments) SELECT DISTINCT + WHERE brand_id = %s + ORDER BY
# 출력: 표 2개 — UNIQLO 옷의 (출처, 종류, 대상 성별) 조합 3행, COVERNAT 1행(source_name·category·target_gender)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/10_브랜드_옷_출처_종류.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: brand_id 하나의 (출처, 종류, 대상 성별) 조합 — 옷이 12벌이어도 조합이 같으면 한 줄
def brand_source_kinds(brand_id=1):
    sql = """
        SELECT DISTINCT g.source_name, g.category, g.target_gender
        FROM garment.garments AS g
        WHERE g.brand_id = %s
        ORDER BY g.source_name, g.category, g.target_gender
    """
    return query(sql, (brand_id,))


if __name__ == "__main__":
    show("brand_id 1 (UNIQLO) 옷의 출처·종류·대상 성별", brand_source_kinds(1))
    show("brand_id 4 (COVERNAT) 옷의 출처·종류·대상 성별", brand_source_kinds(4))
