# 목적: 사람마다 3D 필수 치수 중 빠진 코드 목록, 그리고 필수 코드마다 빠진 사람 수 (3D 에서 추정·기본값으로 채울 곳)
# 누가 쓰나: 3D
# 난이도: 고급 — CROSS JOIN(사람 × 필수 항목 모든 짝) + NOT EXISTS 상관 서브쿼리 + GROUP BY·GROUP_CONCAT
# 출력: 사람별 빠진 3D 필수 치수 표(17행; missing_tally·missing_codes) + 필수 코드별 빠진 사람 수 표(10행; missing_people)
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/04_3D필수치수_누락목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 3D 신체 모델에 꼭 넣을 치수 (2_심화/05_3D필수세트_보유자.py 와 같은 약속값)
REQUIRED_3D = ("height", "chest_girth", "waist_girth", "hip_girth", "shoulder_width",
               "arm_length", "inseam", "neck_girth", "thigh_girth", "upperarm_girth")


# 목적: %s 자리 n 개를 쉼표로 이은 글자 — IN 목록도 값은 %s 로 넘김
def placeholders(n):
    marks = []
    for i in range(n):
        marks.append("%s")
    return ", ".join(marks)


# 목적: 사람마다 빠진 필수 치수 (다 있는 사람은 행이 안 나옴)
def missing_by_profile():
    sql = """
        SELECT p.profile_id, p.source_name, p.gender,
               COUNT(*) AS missing_tally,
               GROUP_CONCAT(d.measure_code ORDER BY d.measure_code SEPARATOR ', ') AS missing_codes
        FROM body.profiles AS p
        CROSS JOIN ref.measure_definitions AS d
        WHERE d.measure_code IN (""" + placeholders(len(REQUIRED_3D)) + """)
          AND NOT EXISTS (
                SELECT 1 FROM body.measures AS m
                WHERE m.profile_id = p.profile_id AND m.measure_code = d.measure_code
          )
        GROUP BY p.profile_id, p.source_name, p.gender
        ORDER BY missing_tally, p.profile_id
    """
    return query(sql, REQUIRED_3D)


# 목적: 필수 코드마다 그 치수가 없는 사람 수 (많이 빠진 것부터 = 추정 모델이 먼저 필요한 것)
def missing_by_code():
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part,
               COUNT(*) AS missing_people
        FROM ref.measure_definitions AS d
        CROSS JOIN body.profiles AS p
        WHERE d.measure_code IN (""" + placeholders(len(REQUIRED_3D)) + """)
          AND NOT EXISTS (
                SELECT 1 FROM body.measures AS m
                WHERE m.profile_id = p.profile_id AND m.measure_code = d.measure_code
          )
        GROUP BY d.measure_code, d.korean_name, d.body_part
        ORDER BY missing_people DESC, d.measure_code
    """
    return query(sql, REQUIRED_3D)


if __name__ == "__main__":
    rows = missing_by_profile()
    show("사람별 빠진 3D 필수 치수", rows)
    print("  → 행이 없는 사람(더미 회원 18~22)은 필수 치수 " + str(len(REQUIRED_3D)) + "개를 모두 가짐")
    show("필수 코드별 빠진 사람 수", missing_by_code())
