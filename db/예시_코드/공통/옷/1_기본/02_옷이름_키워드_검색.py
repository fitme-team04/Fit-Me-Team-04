# 목적: 옷 이름에 낱말이 들어간 옷 찾기 (프론트 검색창, 3D·AI 에서 옷 고르기)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.garments) + WHERE ... LIKE '%낱말%'
# 출력: 이름 검색 표 3개 — '크루넥' 3행, 'T-Shirt' 3행, 'Soft'로 시작 1행 (id·출처·상품번호·이름·성별)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/02_옷이름_키워드_검색.py
# LIKE '%크루넥%' = 앞뒤에 무엇이 오든 "크루넥" 이 들어 있으면 맞음 (% = 아무 글자 0개 이상)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 이름에 keyword 가 들어간 옷 목록
def search_by_name(keyword="크루넥"):
    sql = """
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name, g.target_gender
        FROM garment.garments AS g
        WHERE g.garment_name LIKE %s
        ORDER BY g.garment_id
    """
    pattern = "%" + keyword + "%"
    return query(sql, (pattern,))


# 목적: 옷 이름이 keyword 로 시작하는 옷 목록 (앞부분만 맞추기)
def search_by_name_prefix(keyword="Soft"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name
        FROM garment.garments AS g
        WHERE g.garment_name LIKE %s
        ORDER BY g.garment_name
    """
    pattern = keyword + "%"
    return query(sql, (pattern,))


if __name__ == "__main__":
    show("이름에 '크루넥' 이 들어간 옷", search_by_name("크루넥"))
    show("이름에 'T-Shirt' 가 들어간 옷", search_by_name("T-Shirt"))
    show("이름이 'Soft' 로 시작하는 옷", search_by_name_prefix("Soft"))
