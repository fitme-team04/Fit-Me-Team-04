# 목적: 규칙 기반 사이즈 추천 실행 예시 — 내 신체 치수 ↔ 옷 사이즈별 치수 비교 (함수는 예시_코드/_추천.py). 모델과 비교할 기준
# 누가 쓰나: AI
# 난이도: 고급 — 3개 표 LEFT JOIN 조회 + 대응 규칙(ref.measure_maps)으로 여유분 계산·순위 (db/query/recommend/01~03 과 같은 규칙)
# 출력: profile 1 치수 dict, E422992-000 사이즈별 여유분·fit/small 표 3개(KR 맞는 것 없음·US M·직접 입력 KR M)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/01_규칙_사이즈_추천.py
#  - 여유분(ease) = 옷 치수 × factor − 신체 치수, 모든 항목 ≥ 0 이면 fit / 하나라도 음수면 small
#  - 순위: fit 먼저, 그 안에서 평균 여유분이 작은 순. 권장범위 = 범위 안 항목 수 / 비교 항목 수 (참고용)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _추천 import recommend, body_from_profile                 # 규칙 추천 (예시_코드/_추천.py)


if __name__ == "__main__":
    # 예시: ANSUR II 남성 profile 1 (가슴 107.4 · 어깨 40.1) × UNIQLO 크루넥T(E422992-000)
    body = body_from_profile(1)
    print("profile_id = 1 신체 치수:", body)
    recommend(body, "uniqlo_site", "E422992-000", "KR")
    recommend(body, "uniqlo_site", "E422992-000", "US")
    # 직접 넣은 치수 dict 로도 됨
    recommend({"chest_girth": 92.0, "shoulder_width": 42.0, "waist_girth": 80.0},
              "uniqlo_site", "E422992-000", "KR")
