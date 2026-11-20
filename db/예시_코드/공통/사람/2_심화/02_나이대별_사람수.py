# 목적: 나이대(20대·30대·40대 …)별 사람 수와 평균 키·체중, 사람이 일정 수 이상인 나이대만 고르기
# 누가 쓰나: 공통 (AI 나이대 균형 확인, 3D 나이대별 표본 고르기)
# 난이도: 심화 — 표 1개 GROUP BY 계산식(FLOOR(age / 10) * 10) + HAVING + AVG
# 출력: 표 2개 — 나이대×성별 사람 수·평균 키·체중(5행), 3명 이상 나이대 HAVING(최연소·최고령, 3행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/02_나이대별_사람수.py
# 나이가 NULL 인 사람(BodyM)은 나이대를 알 수 없어 뺌 (1_기본/04_나이_빈값_신체정보.py)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 나이대 × 성별 사람 수·평균 키·평균 체중 (나이대 = 나이를 10 단위로 내림)
def people_by_age_band():
    sql = """
        SELECT FLOOR(p.age / 10) * 10 AS age_band,
               p.gender,
               COUNT(*) AS people_tally,
               ROUND(AVG(p.height_cm), 1) AS avg_height_cm,
               ROUND(AVG(p.weight_kg), 1) AS avg_weight_kg
        FROM body.profiles AS p
        WHERE p.age IS NOT NULL
        GROUP BY FLOOR(p.age / 10) * 10, p.gender
        ORDER BY age_band, p.gender
    """
    return query(sql)


# 목적: 사람이 min_people 명 이상인 나이대만 (그룹을 거르는 조건은 WHERE 가 아니라 HAVING)
def crowded_age_bands(min_people=3):
    sql = """
        SELECT FLOOR(p.age / 10) * 10 AS age_band,
               COUNT(*) AS people_tally,
               MIN(p.age) AS youngest,
               MAX(p.age) AS oldest
        FROM body.profiles AS p
        WHERE p.age IS NOT NULL
        GROUP BY FLOOR(p.age / 10) * 10
        HAVING COUNT(*) >= %s
        ORDER BY age_band
    """
    return query(sql, (min_people,))


if __name__ == "__main__":
    show("나이대 × 성별 사람 수", people_by_age_band())
    show("사람이 3명 이상인 나이대 (HAVING)", crowded_age_bands(3))
