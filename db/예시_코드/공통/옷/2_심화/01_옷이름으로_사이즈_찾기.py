# 목적: 옷 이름 낱말로 찾은 옷의 사이즈까지 한 번에 보기 (번호를 몰라도 이름만으로 사이즈 확인)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 2개 JOIN(garments + sizes) + LIKE 조건
# 출력: 이름+사이즈 표 3개 — '크루넥' KR 8행, '티셔츠' KR 6행, 'mens' US 3행 (id·상품번호·이름·표기·지역)
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/01_옷이름으로_사이즈_찾기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 이름에 keyword 가 든 옷의 사이즈 (지역 하나만)
def sizes_by_name(keyword="크루넥", region="KR"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name, s.size_label, s.region
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        WHERE g.garment_name LIKE %s
          AND s.region = %s
        ORDER BY g.garment_id, s.size_id
    """
    pattern = "%" + keyword + "%"
    return query(sql, (pattern, region))


if __name__ == "__main__":
    show("이름에 '크루넥' 이 든 옷의 KR 사이즈", sizes_by_name("크루넥", "KR"))
    show("이름에 '티셔츠' 가 든 옷의 KR 사이즈", sizes_by_name("티셔츠", "KR"))
    show("이름에 'mens' 가 든 옷의 US 사이즈", sizes_by_name("mens", "US"))
