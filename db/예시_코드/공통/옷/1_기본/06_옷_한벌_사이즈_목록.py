# 목적: garment_id 하나의 사이즈(표기·지역)만 sizes 표에서 바로 보기 — 옷 번호를 이미 알 때 가장 짧은 조회
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.sizes) + WHERE·ORDER BY (출처 + 상품번호로 찾는 JOIN 판은 2_심화/05_옷_사이즈_목록.py)
# 출력: 크루넥T(garment_id 6) 사이즈 11행(size_id·표기·지역), 그 개수 표(11), COVERNAT(id 14) 사이즈 6행
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/06_옷_한벌_사이즈_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 하나(garment_id)의 사이즈 전부 (지역 → 등록 순서)
def sizes_of_garment(garment_id=6):
    sql = """
        SELECT s.size_id, s.size_label, s.region
        FROM garment.sizes AS s
        WHERE s.garment_id = %s
        ORDER BY s.region, s.size_id
    """
    return query(sql, (garment_id,))


# 목적: 옷 하나의 사이즈 개수 (1행)
def size_tally(garment_id=6):
    sql = """
        SELECT COUNT(*) AS size_tally
        FROM garment.sizes AS s
        WHERE s.garment_id = %s
    """
    return query(sql, (garment_id,))


if __name__ == "__main__":
    show("garment_id 6 (UNIQLO 크루넥T E422992-000) 사이즈", sizes_of_garment(6))
    show("garment_id 6 사이즈 개수", size_tally(6))
    show("garment_id 14 (COVERNAT 1848166) 사이즈", sizes_of_garment(14))
