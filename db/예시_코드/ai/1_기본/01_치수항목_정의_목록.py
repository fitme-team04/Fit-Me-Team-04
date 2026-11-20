# 목적: 학습 열(특징·예측 대상) 후보가 되는 신체 치수 항목 정의 목록 보기 — 전체 신체 항목, 부위 하나만
# 누가 쓰나: AI (학습 열 이름 정하기 전 표준 코드 확인)
# 난이도: 기본 — 표 1개(ref.measure_definitions) SELECT + WHERE·ORDER BY
# 출력: ref.measure_definitions 신체 치수 25행(measure_code·korean_name·body_part·measure_type), arm 3행·leg 5행 표
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/01_치수항목_정의_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 신체 치수 항목 정의 (basis = body). 옷 실측 항목(basis = garment)은 사람 치수 학습 대상이 아님
def body_definitions():
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part, d.measure_type
        FROM ref.measure_definitions AS d
        WHERE d.basis = 'body'
        ORDER BY d.body_part, d.measure_code
    """
    return query(sql)


# 목적: 부위 하나(arm / leg / torso / neck / full)의 신체 치수 항목만
def definitions_by_part(body_part):
    sql = """
        SELECT d.measure_code, d.korean_name, d.measure_type
        FROM ref.measure_definitions AS d
        WHERE d.basis = 'body'
          AND d.body_part = %s
        ORDER BY d.measure_code
    """
    return query(sql, (body_part,))


if __name__ == "__main__":
    rows = body_definitions()
    show("신체 치수 항목 (basis = body) — 학습 열 후보", rows)
    show("부위 = arm 만", definitions_by_part("arm"))
    show("부위 = leg 만", definitions_by_part("leg"))
