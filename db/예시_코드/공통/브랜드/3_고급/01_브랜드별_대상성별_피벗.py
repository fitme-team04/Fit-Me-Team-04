# 목적: 브랜드 한 행에 남성·여성·남녀공용 옷 수를 열로 펼친 표 — "이 브랜드는 여성복 위주인가?" 한눈에
# 누가 쓰나: 공통 (3D / AI / 프론트. AI 학습 자료 성별 치우침 확인)
# 난이도: 고급 — 2개 표 LEFT JOIN + 조건부 집계 피벗 SUM(CASE WHEN ... THEN 1 ELSE 0 END) + 비율 계산식
# 출력: 표 1개 — 브랜드별 대상 성별 피벗 4행(male_tally·female_tally·unisex_tally·garment_tally·female_pct)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/01_브랜드별_대상성별_피벗.py
# 세로(옷 1벌 = 1행)를 가로(브랜드 1행, 성별 = 열)로: GROUP BY 브랜드 → 열마다 SUM(CASE WHEN 성별 = '그 값' THEN 1 ELSE 0 END)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드별 대상 성별 피벗 + 여성 옷 비율(%). 옷이 없는 브랜드는 비율 NULL (0 으로 나누지 않게 NULLIF)
def gender_pivot():
    sql = """
        SELECT b.brand_name,
               SUM(CASE WHEN g.target_gender = 'male'   THEN 1 ELSE 0 END) AS male_tally,
               SUM(CASE WHEN g.target_gender = 'female' THEN 1 ELSE 0 END) AS female_tally,
               SUM(CASE WHEN g.target_gender = 'unisex' THEN 1 ELSE 0 END) AS unisex_tally,
               COUNT(g.garment_id) AS garment_tally,
               ROUND(100 * SUM(CASE WHEN g.target_gender = 'female' THEN 1 ELSE 0 END)
                     / NULLIF(COUNT(g.garment_id), 0), 1) AS female_pct
        FROM garment.brands AS b
        LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
        GROUP BY b.brand_id, b.brand_name
        ORDER BY garment_tally DESC, b.brand_id
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드별 대상 성별 옷 수 (피벗)", gender_pivot())
