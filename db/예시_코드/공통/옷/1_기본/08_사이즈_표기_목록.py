# 목적: DB 에서 쓰고 있는 사이즈 표기(size_label: XS / S / M / 95 ...)를 겹치지 않게 보기 — 표기 통일 검사, 프론트 선택지
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.sizes) + DISTINCT / COUNT(DISTINCT ...)
# 출력: 쓰이는 사이즈 표기 8행, US 표기 3행(L·M·S), 가짓수 표 1행(표기 8·지역 2·표기×지역 11)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/08_사이즈_표기_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 쓰이는 사이즈 표기 (글자 순)
def size_labels():
    sql = """
        SELECT DISTINCT s.size_label
        FROM garment.sizes AS s
        ORDER BY s.size_label
    """
    return query(sql)


# 목적: 지역 하나에서 쓰이는 표기
def size_labels_in_region(region="US"):
    sql = """
        SELECT DISTINCT s.size_label
        FROM garment.sizes AS s
        WHERE s.region = %s
        ORDER BY s.size_label
    """
    return query(sql, (region,))


# 목적: 표기·지역·(표기, 지역) 조합이 몇 가지인지 (1행)
def label_kinds():
    sql = """
        SELECT COUNT(DISTINCT s.size_label)           AS label_kinds,
               COUNT(DISTINCT s.region)               AS region_kinds,
               COUNT(DISTINCT s.size_label, s.region) AS label_region_kinds
        FROM garment.sizes AS s
    """
    return query(sql)


if __name__ == "__main__":
    show("쓰이는 사이즈 표기", size_labels())
    show("US 에서 쓰이는 표기", size_labels_in_region("US"))
    show("표기·지역 가짓수", label_kinds())
