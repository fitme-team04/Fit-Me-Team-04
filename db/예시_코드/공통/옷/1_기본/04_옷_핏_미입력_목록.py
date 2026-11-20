# 목적: 핏(fit) 값이 비어 있는(NULL) 옷 찾기 — 수집 때 핏을 못 받은 옷을 골라 채우기 작업 목록으로 씀
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.garments) + WHERE ... IS NULL / IS NOT NULL + COUNT
# 출력: 핏 미입력 옷 14행(fit=NULL), 핏 채움 개수 표(전체 14·채움 0·빈칸 14), 핏 있는 옷 0행(결과 없음)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/04_옷_핏_미입력_목록.py
# NULL 은 = 로 비교하면 항상 거짓이라 반드시 IS NULL 로 씀 (fit = NULL 은 0행)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 핏이 비어 있는 옷 (앞 limit 개)
def garments_without_fit(limit=20):
    sql = """
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name, g.fit
        FROM garment.garments AS g
        WHERE g.fit IS NULL
        ORDER BY g.garment_id
        LIMIT %s
    """
    return query(sql, (limit,))


# 목적: 핏 있음 / 없음 개수 (COUNT(열) 은 NULL 을 빼고 셈, COUNT(*) 는 모든 행)
def fit_fill_tally():
    sql = """
        SELECT COUNT(*)     AS garment_tally,
               COUNT(g.fit) AS fit_filled,
               COUNT(*) - COUNT(g.fit) AS fit_missing
        FROM garment.garments AS g
    """
    return query(sql)


# 목적: 핏이 들어 있는 옷 (자료가 차면 행이 생김, 예시 DB 는 0행)
def garments_with_fit():
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name, g.fit
        FROM garment.garments AS g
        WHERE g.fit IS NOT NULL
        ORDER BY g.fit, g.garment_id
    """
    return query(sql)


if __name__ == "__main__":
    show("핏이 비어 있는 옷 (fit IS NULL, 앞 20개)", garments_without_fit(20))
    show("핏 채움 개수", fit_fill_tally())
    show("핏이 들어 있는 옷 (fit IS NOT NULL)", garments_with_fit())
