# 목적: "나에게 맞는 사이즈" 목록 — 내 최근 신체 치수가 옷 사이즈의 권장 체형 범위(low~high) 안에 몇 항목 들어가는지 사이즈별로 보여 주기
# 누가 쓰나: 프론트 (옷 실측 여유분으로 순위를 매기는 추천은 front/3_고급/10_추천_요청_처리.py)
# 난이도: 심화 — 3개 표 JOIN (body.measures ↔ garment.measures basis=body ↔ garment.sizes) + GROUP BY SUM(CASE BETWEEN)
# 출력: profile 18·20 권장 범위 사이즈 요약 각 2행(M KR·US 맞음/범위 밖)과 항목별 판정 각 4행(범위 안·작음·큼)
# 실행: .venv/bin/python db/예시_코드/front/2_심화/10_내몸_권장범위_사이즈.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: email → 가장 최근 profile_id (없으면 None)
def latest_profile_id(email):
    sql = """
        SELECT p.profile_id
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        WHERE u.email = %s
        ORDER BY p.created_at DESC, p.profile_id DESC
        LIMIT 1
    """
    rows = query(sql, (email,))
    if len(rows) == 0:
        return None
    return rows[0]["profile_id"]


# 목적: 사이즈별 요약: 비교한 항목 수, 범위 안 항목 수 → 모두 안이면 '맞음'
def size_summary(profile_id):
    sql = """
        SELECT s.garment_id, s.size_id, s.size_label, s.region,
               COUNT(*) AS compared,
               SUM(CASE WHEN bm.value_cm BETWEEN gm.low_cm AND gm.high_cm THEN 1 ELSE 0 END) AS in_range
        FROM body.measures AS bm
        JOIN garment.measures AS gm ON gm.measure_code = bm.measure_code AND gm.basis = 'body'
        JOIN garment.sizes    AS s  ON s.size_id = gm.size_id
        WHERE bm.profile_id = %s
        GROUP BY s.garment_id, s.size_id, s.size_label, s.region
        ORDER BY in_range DESC, s.garment_id, s.size_id
    """
    rows = query(sql, (profile_id,))
    for row in rows:
        row["in_range"] = int(row["in_range"])
        if row["in_range"] == row["compared"]:
            row["result"] = "맞음"
        else:
            row["result"] = "범위 밖 항목 있음"
    return rows


# 목적: 사이즈별 항목 자세히: 내 값, 권장 범위, 안/밖 (화면에서 사이즈를 눌렀을 때)
def size_detail(profile_id):
    sql = """
        SELECT s.size_label, s.region, bm.measure_code, bm.value_cm AS my_cm, gm.low_cm, gm.high_cm,
               CASE WHEN bm.value_cm < gm.low_cm THEN '작음'
                    WHEN bm.value_cm > gm.high_cm THEN '큼'
                    ELSE '범위 안' END AS judge
        FROM body.measures AS bm
        JOIN garment.measures AS gm ON gm.measure_code = bm.measure_code AND gm.basis = 'body'
        JOIN garment.sizes    AS s  ON s.size_id = gm.size_id
        WHERE bm.profile_id = %s
        ORDER BY s.size_id, bm.measure_code
    """
    return query(sql, (profile_id,))


if __name__ == "__main__":
    for email in ["user01@example.com", "user03@example.com"]:
        profile_id = latest_profile_id(email)
        show("권장 범위 사이즈 요약 (email = " + email + ", profile_id = " + str(profile_id) + ")",
             size_summary(profile_id))
        show("항목별 자세히 (profile_id = " + str(profile_id) + ")", size_detail(profile_id))
