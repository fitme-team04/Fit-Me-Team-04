# 목적: 학습 샘플 한 명의 치수가 DB 에 어떤 모양(사람 × 치수 = 1행, 세로)으로 들어 있는지 보고 {코드: 값} 으로 바꾸기
# 누가 쓰나: AI (원본 모양 이해 → 2_심화/04 에서 가로 펼치기)
# 난이도: 기본 — 표 1개(body.measures) SELECT + WHERE·ORDER BY·LIMIT
# 출력: profile_id 18 치수 8행(measure_code·value_cm·measure_method), 학습 샘플 dict 18번 23항목·11번 3항목
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/03_한사람_치수_세로보기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 한 사람(profile_id)의 치수 행 (세로 모양). limit 를 주면 앞 몇 줄만
def measures_of(profile_id, limit=100):
    sql = """
        SELECT m.measure_code, m.value_cm, m.measure_method
        FROM body.measures AS m
        WHERE m.profile_id = %s
        ORDER BY m.measure_code
        LIMIT %s
    """
    return query(sql, (profile_id, limit))


# 목적: 세로 행 목록 → 학습 샘플 하나 {measure_code: value_cm}
def to_sample(rows):
    sample = {}
    for row in rows:
        sample[row["measure_code"]] = float(row["value_cm"])
    return sample


if __name__ == "__main__":
    # 18 = 더미 회원 1 (ANSUR II 23항목), 11 = BodyM 한 명 (3항목)
    show("profile_id = 18 치수 앞 8줄 (세로 모양)", measures_of(18, 8))
    for pid in [18, 11]:
        sample = to_sample(measures_of(pid))
        print()
        print("  profile_id = " + str(pid) + " → 학습 샘플 (" + str(len(sample)) + "개 항목):")
        print("  ", sample)
