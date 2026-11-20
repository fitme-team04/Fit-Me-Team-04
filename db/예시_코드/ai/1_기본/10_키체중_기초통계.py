# 목적: 성별마다 키·체중·BMI 의 평균·표준편차·중앙값·범위 구하기 → 특징 표준화(z 점수)에 쓸 값과 한 명의 z 점수 예시
# 누가 쓰나: AI (표준화 기준값 확인)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE(성별·NULL 제외), 통계는 파이썬 statistics
# 출력: 성별(각 11명) 키·체중·BMI 기초통계 표(n·mean·sd·median·min·max), 남성 175cm·75kg 키·체중 z점수
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/10_키체중_기초통계.py
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _body_type import bmi_of                                # BMI 계산 (예시_코드/_body_type.py)


# 목적: 성별 하나의 키·체중 (둘 다 있는 사람만)
def heights_weights(gender):
    sql = """
        SELECT p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.gender = %s
          AND p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
        ORDER BY p.profile_id
    """
    return query(sql, (gender,))


# 목적: 숫자 목록 → 통계 한 행 (2개 미만이면 표준편차 0)
def describe(name, values):
    sd = 0.0
    if len(values) >= 2:
        sd = statistics.stdev(values)
    return {"feature": name, "n": len(values), "mean": round(statistics.mean(values), 2),
            "sd": round(sd, 2), "median": round(statistics.median(values), 2),
            "min": round(min(values), 2), "max": round(max(values), 2)}


# 목적: 성별 하나의 키·체중·BMI 통계 행 3개
def stats_for(gender):
    heights = []
    weights = []
    bmis = []
    for row in heights_weights(gender):
        heights.append(float(row["height_cm"]))
        weights.append(float(row["weight_kg"]))
        bmis.append(bmi_of(row["height_cm"], row["weight_kg"]))
    return [describe("height_cm", heights), describe("weight_kg", weights), describe("bmi", bmis)]


# 목적: z 점수 = (값 − 평균) / 표준편차 (표준편차 0 이면 0)
def z_score(value, stat):
    if stat["sd"] == 0:
        return 0.0
    return round((value - stat["mean"]) / stat["sd"], 3)


if __name__ == "__main__":
    for gender in ["male", "female"]:
        show("기초 통계 (gender = " + gender + ")", stats_for(gender))
    male = stats_for("male")
    print()
    print("  예: 남성 175.0cm · 75.0kg → 키 z =", z_score(175.0, male[0]), "/ 체중 z =", z_score(75.0, male[1]))
