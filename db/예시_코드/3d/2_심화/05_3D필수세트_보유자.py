# 목적: 3D 신체 모델에 꼭 필요한 치수 10개를 모두 가진 사람 / 일부만 가진 사람 찾기
# 누가 쓰나: 3D
# 난이도: 심화 — 2개 표 JOIN(body.profiles + body.measures) + WHERE IN + GROUP BY + HAVING COUNT(DISTINCT)
# 출력: 3D 필수 치수 10개 목록 + 10/10 보유자 표(5행)·일부(1~9개) 보유자 표(5행); gender·source_name·required_have
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/05_3D필수세트_보유자.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 3D 신체 모델(뼈 길이 + 주요 단면)에 꼭 넣을 치수 (예시 약속값)
REQUIRED_3D = ("height", "chest_girth", "waist_girth", "hip_girth", "shoulder_width",
               "arm_length", "inseam", "neck_girth", "thigh_girth", "upperarm_girth")


# 목적: %s 자리 n 개를 쉼표로 이은 글자 ("%s, %s, %s") — IN 목록도 값은 %s 로 넘김
def placeholders(n):
    marks = []
    for i in range(n):
        marks.append("%s")
    return ", ".join(marks)


# 목적: 필수 치수를 have_min 개 이상 have_max 개 이하로 가진 사람 + 가진 개수
def profiles_by_required_tally(have_min, have_max):
    sql = """
        SELECT p.profile_id, p.gender, p.source_name, p.body_type,
               COUNT(DISTINCT m.measure_code) AS required_have
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.measure_code IN (""" + placeholders(len(REQUIRED_3D)) + """)
        GROUP BY p.profile_id, p.gender, p.source_name, p.body_type
        HAVING COUNT(DISTINCT m.measure_code) BETWEEN %s AND %s
        ORDER BY required_have DESC, p.profile_id
    """
    params = list(REQUIRED_3D)
    params.append(have_min)
    params.append(have_max)
    return query(sql, tuple(params))


if __name__ == "__main__":
    total = len(REQUIRED_3D)
    print("3D 필수 치수 (" + str(total) + "개):", list(REQUIRED_3D))
    show("필수 치수를 모두 가진 사람 (" + str(total) + "/" + str(total) + ")",
         profiles_by_required_tally(total, total))
    show("필수 치수를 일부만 가진 사람 (1 ~ " + str(total - 1) + "개)",
         profiles_by_required_tally(1, total - 1))
