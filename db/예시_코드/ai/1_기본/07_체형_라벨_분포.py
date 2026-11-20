# 목적: 분류 정답(라벨)으로 쓸 체형(body_type) 값마다 몇 명인지 = 클래스 균형 보기 (전체, 성별 하나)
# 누가 쓰나: AI (클래스가 한쪽에 몰렸는지 확인)
# 난이도: 기본 — 표 1개(body.profiles) COUNT(*) + WHERE, 체형 값마다 파이썬 for 로 여러 번 (GROUP BY 없이)
# 출력: 체형 6종 분포 표(tally·pct) 전체 22명(obese_1 7명 최다, 불균형 7.0)과 female 11명
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/07_체형_라벨_분포.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _body_type import BODY_TYPES, body_type_name            # 체형 허용값·한글 이름 (예시_코드/_body_type.py)


# 목적: 체형 하나의 사람 수. gender 를 주면 그 성별만
def count_body_type(body_type, gender=None):
    sql = """
        SELECT COUNT(*) AS tally
        FROM body.profiles AS p
        WHERE p.body_type = %s
          AND (%s IS NULL OR p.gender = %s)
    """
    return query(sql, (body_type, gender, gender))[0]["tally"]


# 목적: 체형이 비어 있는(NULL, 키·체중이 없어 계산 못 한) 사람 수
def count_unlabeled():
    sql = """
        SELECT COUNT(*) AS tally
        FROM body.profiles AS p
        WHERE p.body_type IS NULL
    """
    return query(sql)[0]["tally"]


# 목적: 체형 값마다 사람 수·비율 표
def distribution(gender=None):
    tallies = []
    total = 0
    for bt in BODY_TYPES:
        tally = count_body_type(bt, gender)
        tallies.append(tally)
        total += tally
    rows = []
    for i in range(len(BODY_TYPES)):
        pct = 0.0
        if total > 0:
            pct = round(tallies[i] * 100.0 / total, 1)
        rows.append({"body_type": BODY_TYPES[i], "korean_name": body_type_name(BODY_TYPES[i]),
                     "tally": tallies[i], "pct": pct})
    return rows


# 목적: 가장 많은 클래스 ÷ 가장 적은 클래스(0 명 제외) = 불균형 비율
def imbalance_ratio(rows):
    counts = []
    for row in rows:
        if row["tally"] > 0:
            counts.append(row["tally"])
    if len(counts) == 0:
        return None
    return round(max(counts) / min(counts), 2)


if __name__ == "__main__":
    rows = distribution()
    show("체형 라벨 분포 (전체)", rows)
    print("  체형 없음(NULL):", count_unlabeled(), "명 / 불균형 비율(최다 ÷ 최소):", imbalance_ratio(rows))
    show("체형 라벨 분포 (gender = female)", distribution("female"))
    empty = []
    for row in rows:
        if row["tally"] == 0:
            empty.append(row["body_type"])
    if len(empty) > 0:
        print("  · 한 명도 없는 클래스:", ", ".join(empty), "→ 분류 모델이 배울 수 없음")
