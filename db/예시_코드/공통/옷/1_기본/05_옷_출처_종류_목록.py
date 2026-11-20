# 목적: 옷이 어느 출처(source_name)·종류(category)에서 왔는지 겹치지 않게 보기 (프론트 필터 선택지, AI 데이터 범위 확인)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.garments) + DISTINCT / COUNT(DISTINCT ...)
# 출력: 출처+종류 조합 3행, 가짓수 표 1행(출처 3·종류 1·성별 3), uniqlo_site 상의 개수 표(12)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/05_옷_출처_종류_목록.py
# DISTINCT = 같은 값이 여러 행이어도 한 번만 보여 줌
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 출처 + 종류 조합 (겹치지 않게)
def source_category_pairs():
    sql = """
        SELECT DISTINCT g.source_name, g.category
        FROM garment.garments AS g
        ORDER BY g.source_name, g.category
    """
    return query(sql)


# 목적: 출처·종류·대상 성별이 각각 몇 가지인지 (1행)
def distinct_tally():
    sql = """
        SELECT COUNT(DISTINCT g.source_name)   AS source_kinds,
               COUNT(DISTINCT g.category)      AS category_kinds,
               COUNT(DISTINCT g.target_gender) AS gender_kinds
        FROM garment.garments AS g
    """
    return query(sql)


# 목적: 출처 하나 + 종류 하나에 해당하는 옷 개수 (1행)
def tally_by_source_category(source_name="uniqlo_site", category="상의"):
    sql = """
        SELECT COUNT(*) AS garment_tally
        FROM garment.garments AS g
        WHERE g.source_name = %s
          AND g.category = %s
    """
    return query(sql, (source_name, category))


if __name__ == "__main__":
    show("출처 + 종류 조합", source_category_pairs())
    show("출처·종류·성별 가짓수", distinct_tally())
    show("uniqlo_site 의 상의 개수", tally_by_source_category("uniqlo_site", "상의"))
