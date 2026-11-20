# 목적: 성별마다 사람 수와 키·체중의 평균·최소·최대 (데이터 전체 체격 한눈에 보기)
# 누가 쓰나: 공통 (AI 데이터 살펴보기, 3D 성별 기본 몸 크기, 프론트 통계 화면)
# 난이도: 심화 — 표 1개 GROUP BY + 집계 함수 AVG·MIN·MAX·COUNT, 선택 조건(출처)
# 출력: 표 2개 — 성별 사람 수·키·체중 평균/최소/최대(전체, 2행), 같은 요약 ansur2 만(2행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/01_성별_평균_키체중.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 성별마다 키·체중 요약. source_name 을 주면 그 출처만, None 이면 전체
def height_weight_by_gender(source_name=None):
    sql = """
        SELECT p.gender,
               COUNT(*) AS people_tally,
               ROUND(AVG(p.height_cm), 1) AS avg_height_cm,
               MIN(p.height_cm) AS min_height_cm,
               MAX(p.height_cm) AS max_height_cm,
               ROUND(AVG(p.weight_kg), 1) AS avg_weight_kg,
               MIN(p.weight_kg) AS min_weight_kg,
               MAX(p.weight_kg) AS max_weight_kg
        FROM body.profiles AS p
        WHERE (%s IS NULL OR p.source_name = %s)
        GROUP BY p.gender
        ORDER BY p.gender
    """
    return query(sql, (source_name, source_name))


if __name__ == "__main__":
    show("성별 키·체중 요약 (전체)", height_weight_by_gender(None))
    show("성별 키·체중 요약 (ansur2 만)", height_weight_by_gender("ansur2"))
