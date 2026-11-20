# 목적: 성별마다 치수 평균 → 3D 성별 기본 몸(템플릿) 값. 표본이 적은 항목은 HAVING 으로 뺌
# 누가 쓰나: 3D
# 난이도: 심화 — 뷰(body.measure_details = 치수 + 정의) + body.profiles JOIN = 3개 표 + GROUP BY 3열 + HAVING
# 출력: 성별 기본 몸 표 — 몸통(표본 3명+, 18행)·다리(표본 2명+, 8행); gender·measure_code·people·template_cm·spread_cm
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/09_성별_기본몸_평균치수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 성별 × 치수 평균 (부위 하나). 표본이 min_people 명 이상인 항목만
def template_means(body_part, min_people):
    sql = """
        SELECT p.gender, md.measure_code, md.korean_name,
               COUNT(*) AS people,
               ROUND(AVG(md.value_cm), 1) AS template_cm,
               ROUND(STDDEV_POP(md.value_cm), 1) AS spread_cm
        FROM body.measure_details AS md
        JOIN body.profiles AS p ON p.profile_id = md.profile_id
        WHERE md.body_part = %s
        GROUP BY p.gender, md.measure_code, md.korean_name
        HAVING COUNT(*) >= %s
        ORDER BY md.measure_code, p.gender
    """
    return query(sql, (body_part, min_people))


if __name__ == "__main__":
    # 몸통: ANSUR II·BodyM·더미 회원이 모두 있어 표본이 큼 → 3명 이상만
    show("성별 기본 몸 — 몸통 (표본 3명 이상)", template_means("torso", 3))
    # 다리: 더미 회원(남 3 · 여 2)만 있음 → 2명 이상
    show("성별 기본 몸 — 다리 (표본 2명 이상)", template_means("leg", 2))
