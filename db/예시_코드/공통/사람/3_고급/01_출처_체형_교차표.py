# 목적: 출처(ansur2·bodym·user) × 체형(body_type) 교차표 — 출처 1개 = 1행, 체형마다 1열 + 비만(obese_*) 비율
# 누가 쓰나: 공통 (AI 출처별 체형 치우침 확인, 3D 체형별 표본이 어느 출처에 있는지)
# 난이도: 고급 — 조건부 집계 피벗 SUM(CASE WHEN ... THEN 1 ELSE 0 END) 6열 + 비율 계산식 + WITH ROLLUP 합계 행
# 출력: 표 3개 — 출처×체형 6단계 교차표+비만율%·합계 행(4행), 성별×체형 교차표 전체(2행)·회원 user 만(2행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/01_출처_체형_교차표.py
# 체형 값: _body_type.py BODY_TYPES (대한비만학회 BMI 단계)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 출처 × 체형 사람 수 피벗 + 비만(1~3단계) 비율 %. 마지막 행(source_name = NULL)은 WITH ROLLUP 합계
def source_body_type_table():
    sql = """
        SELECT p.source_name,
               SUM(CASE WHEN p.body_type = 'underweight' THEN 1 ELSE 0 END) AS underweight,
               SUM(CASE WHEN p.body_type = 'normal'      THEN 1 ELSE 0 END) AS normal,
               SUM(CASE WHEN p.body_type = 'pre_obese'   THEN 1 ELSE 0 END) AS pre_obese,
               SUM(CASE WHEN p.body_type = 'obese_1'     THEN 1 ELSE 0 END) AS obese_1,
               SUM(CASE WHEN p.body_type = 'obese_2'     THEN 1 ELSE 0 END) AS obese_2,
               SUM(CASE WHEN p.body_type = 'obese_3'     THEN 1 ELSE 0 END) AS obese_3,
               COUNT(*) AS people_tally,
               ROUND(100 * SUM(CASE WHEN p.body_type IN ('obese_1', 'obese_2', 'obese_3') THEN 1 ELSE 0 END)
                     / COUNT(*), 1) AS obese_pct
        FROM body.profiles AS p
        GROUP BY p.source_name WITH ROLLUP
    """
    rows = query(sql)
    for row in rows:
        if row["source_name"] is None:
            row["source_name"] = "(합계)"
    return rows


# 목적: 성별 × 체형 교차표 (같은 피벗을 성별 하나에 대해, 출처 조건은 선택)
def gender_body_type_table(source_name=None):
    sql = """
        SELECT p.gender,
               SUM(CASE WHEN p.body_type = 'underweight' THEN 1 ELSE 0 END) AS underweight,
               SUM(CASE WHEN p.body_type = 'normal'      THEN 1 ELSE 0 END) AS normal,
               SUM(CASE WHEN p.body_type = 'pre_obese'   THEN 1 ELSE 0 END) AS pre_obese,
               SUM(CASE WHEN p.body_type = 'obese_1'     THEN 1 ELSE 0 END) AS obese_1,
               SUM(CASE WHEN p.body_type = 'obese_2'     THEN 1 ELSE 0 END) AS obese_2,
               SUM(CASE WHEN p.body_type = 'obese_3'     THEN 1 ELSE 0 END) AS obese_3,
               COUNT(*) AS people_tally
        FROM body.profiles AS p
        WHERE (%s IS NULL OR p.source_name = %s)
        GROUP BY p.gender
        ORDER BY p.gender
    """
    return query(sql, (source_name, source_name))


if __name__ == "__main__":
    show("출처 × 체형 교차표 (+ 비만 비율 %, 합계 행)", source_body_type_table())
    show("성별 × 체형 교차표 (전체)", gender_body_type_table(None))
    show("성별 × 체형 교차표 (회원 user 만)", gender_body_type_table("user"))
