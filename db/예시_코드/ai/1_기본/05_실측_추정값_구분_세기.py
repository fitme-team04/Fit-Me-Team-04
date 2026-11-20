# 목적: 치수 행 중 실측(measured)과 AI 추정(estimated)이 각각 몇 개인지 세기 — 학습에 추정값이 섞이지 않게 확인
# 누가 쓰나: AI (학습은 실측만, 추정값은 모델 출력이라 다시 학습에 넣으면 안 됨)
# 난이도: 기본 — 표 1개(body.measures) COUNT(*)·COUNT(DISTINCT) + WHERE, SELECT DISTINCT
# 출력: 실측 134행·10명 / 추정 0행 표, (measure_method, model_version) 1종(measured, NULL) — 추정값 없음 확인
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/05_실측_추정값_구분_세기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

METHODS = ["measured", "estimated"]                  # body.measures.measure_method 허용값


# 목적: 방법(measured / estimated) 하나의 치수 행 수와 사람 수
def count_method(method):
    sql = """
        SELECT COUNT(*) AS row_tally,
               COUNT(DISTINCT m.profile_id) AS profile_tally
        FROM body.measures AS m
        WHERE m.measure_method = %s
    """
    return query(sql, (method,))[0]


# 목적: (방법, 모델 버전) 짝의 종류. 실측은 model_version 이 NULL, 추정은 만든 모델 이름이 들어 있어야 함
def method_versions():
    sql = """
        SELECT DISTINCT m.measure_method, m.model_version
        FROM body.measures AS m
        ORDER BY m.measure_method, m.model_version
    """
    return query(sql)


if __name__ == "__main__":
    rows = []
    for method in METHODS:
        tally = count_method(method)
        use = "학습에 씀"
        if method == "estimated":
            use = "학습에서 뺌 (모델 출력)"
        rows.append({"measure_method": method, "row_tally": tally["row_tally"],
                     "profile_tally": tally["profile_tally"], "use": use})
    show("치수 행 실측 / 추정 구분", rows)
    versions = method_versions()
    show("(measure_method, model_version) 종류", versions)
    estimated = 0
    for row in versions:
        if row["measure_method"] == "estimated":
            estimated += 1
    if estimated == 0:
        print("  → 지금 DB 에는 추정값이 없음 = 학습 표에 섞일 걱정 없음 (front 저장 예시는 rollback 이라 남지 않음)")
