# 목적: 사이즈 표기 체계(region: KR / US / JP ...)로 사이즈 거르기 — 지역 하나, 지역 여러 개, 지역 하나의 개수
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.sizes) + WHERE = / IN (...) + ORDER BY·LIMIT·COUNT
# 출력: US 표기 사이즈 6행(size_id·garment_id·표기·지역), KR·US 의 M 사이즈 4행, KR 사이즈 개수 표(14)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/07_지역별_사이즈_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 지역 하나의 사이즈 (앞 limit 개)
def sizes_by_region(region="US", limit=20):
    sql = """
        SELECT s.size_id, s.garment_id, s.size_label, s.region
        FROM garment.sizes AS s
        WHERE s.region = %s
        ORDER BY s.garment_id, s.size_id
        LIMIT %s
    """
    return query(sql, (region, limit))


# 목적: 지역 두 개의 사이즈 중 표기 하나(예: M)만
def label_in_regions(size_label="M", region_a="KR", region_b="US"):
    sql = """
        SELECT s.size_id, s.garment_id, s.size_label, s.region
        FROM garment.sizes AS s
        WHERE s.size_label = %s
          AND s.region IN (%s, %s)
        ORDER BY s.garment_id, s.region
    """
    return query(sql, (size_label, region_a, region_b))


# 목적: 지역 하나의 사이즈 개수 (1행)
def region_tally(region="KR"):
    sql = """
        SELECT COUNT(*) AS size_tally
        FROM garment.sizes AS s
        WHERE s.region = %s
    """
    return query(sql, (region,))


if __name__ == "__main__":
    show("US 표기 사이즈", sizes_by_region("US", 20))
    show("KR·US 의 M 사이즈", label_in_regions("M", "KR", "US"))
    show("KR 표기 사이즈 개수", region_tally("KR"))
