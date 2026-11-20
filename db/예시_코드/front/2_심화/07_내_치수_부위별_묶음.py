# 목적: "내 치수" 화면의 부위 탭(몸통·팔·다리 ...) — 탭마다 항목 수·실측/추정 수 요약 + 탭 안 목록 묶음
# 누가 쓰나: 프론트 (평평한 한 목록은 front/2_심화/06_내_치수_한글이름.py)
# 난이도: 심화 — 표 2개(users · profiles) + 뷰 1개(body.measure_details) JOIN, GROUP BY body_part 집계 + 파이썬 묶기
# 출력: user02 부위 탭 요약 5행(측정·추정 개수), 탭별 치수(name·value_cm): 몸통 14행·팔 3행·다리 4행
# 실행: .venv/bin/python db/예시_코드/front/2_심화/07_내_치수_부위별_묶음.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

PART_NAMES = {"full": "전신", "neck": "목", "torso": "몸통", "arm": "팔", "leg": "다리"}


# 목적: email 의 가장 최근 신체 정보 치수를 부위별로 집계 (탭 이름 옆 숫자)
def part_summary(email):
    sql = """
        SELECT md.body_part,
               COUNT(*) AS measure_tally,
               SUM(CASE WHEN md.measure_method = 'measured' THEN 1 ELSE 0 END) AS measured_tally,
               SUM(CASE WHEN md.measure_method = 'estimated' THEN 1 ELSE 0 END) AS estimated_tally
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        JOIN body.measure_details AS md ON md.profile_id = p.profile_id
        WHERE u.email = %s
          AND p.profile_id = (SELECT p2.profile_id FROM body.profiles AS p2
                              WHERE p2.user_id = u.user_id
                              ORDER BY p2.created_at DESC, p2.profile_id DESC LIMIT 1)
        GROUP BY md.body_part
        ORDER BY FIELD(md.body_part, 'full', 'neck', 'torso', 'arm', 'leg')
    """
    return query(sql, (email,))


# 목적: 같은 사람의 치수 전부 → {부위: [{"name", "value_cm"}]} (탭 안에 그릴 목록)
def measures_by_part(email):
    sql = """
        SELECT md.body_part, md.korean_name, md.value_cm
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        JOIN body.measure_details AS md ON md.profile_id = p.profile_id
        WHERE u.email = %s
          AND p.profile_id = (SELECT p2.profile_id FROM body.profiles AS p2
                              WHERE p2.user_id = u.user_id
                              ORDER BY p2.created_at DESC, p2.profile_id DESC LIMIT 1)
        ORDER BY md.korean_name
    """
    groups = {}
    for row in query(sql, (email,)):
        part = row["body_part"]
        if part not in groups:
            groups[part] = []
        groups[part].append({"name": row["korean_name"], "value_cm": float(row["value_cm"])})
    return groups


if __name__ == "__main__":
    email = "user02@example.com"
    summary = part_summary(email)
    for row in summary:
        row["tab"] = PART_NAMES.get(row["body_part"], row["body_part"])
    show("부위 탭 요약 (email = " + email + ")", summary)

    groups = measures_by_part(email)
    for part in ["torso", "arm", "leg"]:
        if part in groups:
            show("탭: " + PART_NAMES[part], groups[part])
