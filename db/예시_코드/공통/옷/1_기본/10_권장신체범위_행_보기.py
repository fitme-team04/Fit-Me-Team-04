# 목적: 권장 신체 범위 행(basis = body, low_cm ~ high_cm)만 보기 + 범위 폭 계산 — 옷 실측과 저장 방식이 다른 행 이해하기
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.measures) + WHERE 여러 조건(= / IS NULL / IS NOT NULL) + 계산 열 + 정렬 2단
# 출력: 권장 신체 범위 행 4행(size_id·치수코드·low·high·range_cm), 가슴둘레 94cm 가 범위 안인 행 1행
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/10_권장신체범위_행_보기.py
# garment.measures 는 한 표에 두 종류: basis = garment 는 value_cm 하나, basis = body 는 low_cm ~ high_cm (value_cm 은 NULL)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 권장 신체 범위 행 전부 + 범위 폭(high − low)
def body_range_rows():
    sql = """
        SELECT gm.size_id, gm.measure_code, gm.low_cm, gm.high_cm,
               gm.high_cm - gm.low_cm AS range_cm
        FROM garment.measures AS gm
        WHERE gm.basis = 'body'
          AND gm.value_cm IS NULL
          AND gm.low_cm IS NOT NULL
        ORDER BY gm.measure_code, gm.low_cm
    """
    return query(sql)


# 목적: 신체 치수 하나(예: 가슴둘레 94 cm)가 권장 범위 안에 드는 행
def ranges_containing(measure_code="chest_girth", body_cm=94):
    sql = """
        SELECT gm.size_id, gm.measure_code, gm.low_cm, gm.high_cm
        FROM garment.measures AS gm
        WHERE gm.basis = 'body'
          AND gm.measure_code = %s
          AND gm.low_cm <= %s
          AND gm.high_cm >= %s
        ORDER BY gm.size_id
    """
    return query(sql, (measure_code, body_cm, body_cm))


if __name__ == "__main__":
    show("권장 신체 범위 행 (basis = body)", body_range_rows())
    show("가슴둘레 94 cm 가 범위 안인 행", ranges_containing("chest_girth", 94))
