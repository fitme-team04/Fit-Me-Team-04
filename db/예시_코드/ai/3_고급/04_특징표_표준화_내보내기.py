# 목적: 모델 입력용 특징표(feature table) 만들기 — 1명 = 1행, BMI·회원/자세 여부·주요 치수 피벗 + 성별 안 표준화(z)·백분위를 SQL 로 계산 → CSV
# 누가 쓰나: AI (학습 스크립트에 바로 넣을 특징표)
# 난이도: 고급 — 5개 표(profiles·measures·measure_definitions·users·poses) JOIN·LEFT JOIN + CTE + 피벗(MAX CASE) + 계산식(BMI) + 창 함수(AVG·STDDEV_SAMP·PERCENT_RANK OVER)
# 출력: 특징표 CSV 10명·20열(bmi·is_member·height_z 등), 파생 특징 10행 표, 성별 height_z 평균 0·sd 1 검산
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/04_특징표_표준화_내보내기.py            (CSV 를 화면에 출력)
#       .venv/bin/python db/예시_코드/ai/3_고급/04_특징표_표준화_내보내기.py --save     (out/ai/features.csv 로도 저장)
# 2_심화/04 학습 표(원값 그대로)와 달리, 여기는 모델에 넣을 파생 특징(z 점수·비율·백분위)까지 붙임
import csv
import io
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show, save_text

FEATURE_SQL = """
    WITH wide AS (
        SELECT p.profile_id, p.source_name, p.gender,
               CASE WHEN p.gender = 'male' THEN 1 ELSE 0 END AS is_male,
               p.height_cm, p.weight_kg,
               ROUND(p.weight_kg / POW(p.height_cm / 100, 2), 1) AS bmi,
               p.body_type,
               CASE WHEN u.user_id IS NULL THEN 0 ELSE 1 END AS is_member,
               CASE WHEN po.profile_id IS NULL THEN 0 ELSE 1 END AS has_pose,
               MAX(CASE WHEN m.measure_code = 'chest_girth'    THEN m.value_cm END) AS chest_girth,
               MAX(CASE WHEN m.measure_code = 'waist_girth'    THEN m.value_cm END) AS waist_girth,
               MAX(CASE WHEN m.measure_code = 'hip_girth'      THEN m.value_cm END) AS hip_girth,
               MAX(CASE WHEN m.measure_code = 'shoulder_width' THEN m.value_cm END) AS shoulder_width,
               SUM(CASE WHEN d.body_part = 'torso' THEN 1 ELSE 0 END) AS torso_tally,
               COUNT(*) AS measure_tally
        FROM body.profiles AS p
        JOIN body.measures AS m
          ON m.profile_id = p.profile_id
         AND m.measure_method = 'measured'
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        LEFT JOIN body.users AS u ON u.user_id = p.user_id
        LEFT JOIN body.poses AS po ON po.profile_id = p.profile_id
        WHERE p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
          AND (%s IS NULL OR p.source_name = %s)
        GROUP BY p.profile_id, u.user_id, po.profile_id
    )
    SELECT w.*,
           ROUND((w.height_cm - AVG(w.height_cm) OVER (PARTITION BY w.gender))
                 / NULLIF(STDDEV_SAMP(w.height_cm) OVER (PARTITION BY w.gender), 0), 3) AS height_z,
           ROUND((w.weight_kg - AVG(w.weight_kg) OVER (PARTITION BY w.gender))
                 / NULLIF(STDDEV_SAMP(w.weight_kg) OVER (PARTITION BY w.gender), 0), 3) AS weight_z,
           ROUND(PERCENT_RANK() OVER (PARTITION BY w.gender ORDER BY w.chest_girth), 3) AS chest_pct_rank,
           ROUND(w.waist_girth / NULLIF(w.hip_girth, 0), 3) AS waist_hip_ratio
    FROM wide AS w
    ORDER BY w.gender, w.profile_id
"""


# 목적: 특징표 읽기. source_name 을 주면 그 출처만 (표준화도 그 안에서)
def feature_rows(source_name=None):
    return query(FEATURE_SQL, (source_name, source_name))


# 목적: 표 → CSV 글자 (None 은 빈칸)
def to_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    if len(rows) == 0:
        return ""
    columns = list(rows[0].keys())
    writer.writerow(columns)
    for row in rows:
        cells = []
        for col in columns:
            if row[col] is None:
                cells.append("")
            else:
                cells.append(row[col])
        writer.writerow(cells)
    return buffer.getvalue()


# 목적: 표에서 몇 열만 골라 보기 (화면 폭 줄이기)
def pick(rows, columns):
    result = []
    for row in rows:
        item = {}
        for col in columns:
            item[col] = row[col]
        result.append(item)
    return result


# 목적: 검산: 성별마다 z 점수의 평균 ≈ 0, 표준편차 ≈ 1 인지
def check_z(rows):
    result = []
    for gender in ["male", "female"]:
        values = []
        for row in rows:
            if row["gender"] == gender and row["height_z"] is not None:
                values.append(float(row["height_z"]))
        if len(values) < 2:
            continue
        result.append({"gender": gender, "n": len(values),
                       "height_z_mean": round(statistics.mean(values), 3),
                       "height_z_sd": round(statistics.stdev(values), 3)})
    return result


if __name__ == "__main__":
    rows = feature_rows()
    text = to_csv(rows)
    print("■ 특징표 CSV (" + str(len(rows)) + "명, " + str(len(rows[0])) + "열)")
    print(text, end="")
    if "--save" in sys.argv:
        path = save_text("ai/features.csv", text)
        print("  → 저장: " + str(path))
    show("파생 특징만 보기", pick(rows, ["profile_id", "gender", "bmi", "is_member", "has_pose",
                                     "height_z", "weight_z", "chest_pct_rank", "waist_hip_ratio"]))
    show("검산: 성별 안 height_z 평균 0 · 표준편차 1", check_z(rows))
