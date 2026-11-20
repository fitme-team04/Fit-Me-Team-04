# 목적: "치수 수정" 저장 — 이미 있는 치수는 값 수정, 없던 치수는 추가(upsert)하고 항목마다 전/후 차이표를 보여 줌, 예시는 rollback
# 누가 쓰나: 프론트 (치수 입력 칸 목록은 front/2_심화/08_내_치수_입력현황.py)
# 난이도: 고급 — 트랜잭션 INSERT ... ON DUPLICATE KEY UPDATE 여러 행 + 전/후 비교(추가·수정·그대로) + rollback
# 출력: profile 18 치수 전/후 4행(수정·그대로·추가), 개수 23→25 → 되돌림 (rollback) 뒤 다시 센 개수 23
# 실행: .venv/bin/python db/예시_코드/front/3_고급/03_치수_추가수정_롤백.py   (commit=False → DB 는 그대로)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, execute_many, query, query_in, show
from _검증 import MEASURE_MIN, MEASURE_MAX, check_number

UPSERT_SQL = """
    INSERT INTO body.measures (profile_id, measure_code, value_cm, measure_method, model_version)
    VALUES (%s, %s, %s, 'measured', NULL) AS new
    ON DUPLICATE KEY UPDATE value_cm = new.value_cm, measure_method = new.measure_method,
                            model_version = new.model_version
"""


# 목적: 열린 접속에서 profile 의 치수 → {measure_code: value_cm(float)}
def measures_of(conn, profile_id):
    rows = query_in(conn, "SELECT measure_code, value_cm FROM body.measures WHERE profile_id = %s", (profile_id,))
    values = {}
    for row in rows:
        values[row["measure_code"]] = float(row["value_cm"])
    return values


# 목적: 전/후 값 → 차이표 행 목록 (바꾸려고 보낸 코드만)
def diff_rows(before, after, codes):
    rows = []
    for code in codes:
        old = before.get(code)
        new = after.get(code)
        change = "그대로"
        if old is None and new is not None:
            change = "추가"
        elif old is not None and new != old:
            change = "수정"
        rows.append({"measure_code": code, "before": old, "after": new, "change": change})
    return rows


# 목적: 치수 저장 본체. measures = {measure_code: value_cm}
def save_measures(profile_id, measures, commit=True):
    errors = []
    for code in measures:
        check_number(errors, "measures." + code, measures[code], MEASURE_MIN, MEASURE_MAX)
    if len(errors) > 0:
        raise ValueError("입력 오류: " + " / ".join(errors))

    conn = connect()
    try:
        before = measures_of(conn, profile_id)
        rows = []
        for code in measures:
            rows.append((profile_id, code, measures[code]))
        affected = execute_many(conn, UPSERT_SQL, rows)    # MySQL: 추가 1, 수정 2, 그대로 0 씩 더해짐
        after = measures_of(conn, profile_id)
        show("치수 전/후 (profile_id = " + str(profile_id) + ", 같은 접속)", diff_rows(before, after, list(measures)))
        print("  치수 개수: " + str(len(before)) + " → " + str(len(after)) + ", affected rows = " + str(affected))
        if commit:
            conn.commit()
            print("\n  → 저장함 (commit)")
        else:
            conn.rollback()
            print("\n  → 되돌림 (rollback): commit=False 라 DB 에 저장하지 않음")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"profile_id": profile_id, "before_tally": len(before), "after_tally": len(after), "committed": commit}


if __name__ == "__main__":
    # profile 18 = user01 의 신체 정보. 가슴둘레 94.1 → 95.0 수정, 어깨너비 42.9 그대로, 배둘레·무릎둘레(빈 칸) 추가
    result = save_measures(18, {"chest_girth": 95.0, "shoulder_width": 42.9,
                                "stomach_girth": 80.5, "knee_girth": 37.0}, commit=False)
    print("  결과:", result)
    rows = query("SELECT COUNT(*) AS tally FROM body.measures WHERE profile_id = %s", (18,))
    print("  rollback 뒤 새 접속으로 센 profile 18 치수 개수:", rows[0]["tally"])
