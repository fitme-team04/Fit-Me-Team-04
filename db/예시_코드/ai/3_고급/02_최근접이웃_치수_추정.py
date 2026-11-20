# 목적: 치수 추정 기준선 실행 예시 — 성별·키·체중 → 비슷한 실측자 k 명(k-최근접 이웃)의 치수 평균 (함수는 예시_코드/_추정.py)
# 누가 쓰나: AI
# 난이도: 고급 — 2개 표 JOIN 조회 + 파이썬 k-최근접 이웃(표준화 거리) 계산
# 출력: 남 175cm·75kg, 여 160cm·60kg 각각 k=5 이웃 5명(distance)과 추정 치수 22행(value_cm·neighbor_tally)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/02_최근접이웃_치수_추정.py
# 주의: 예시 DB 에는 치수를 잰 사람이 몇 명뿐이라 결과는 거친 기준선임.
#       ANSUR II / BodyM 전체를 적재하면 같은 코드로 더 정확해짐
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _추정 import estimate, print_note, MODEL_VERSION           # k-NN 치수 추정 (예시_코드/_추정.py)


if __name__ == "__main__":
    print("model_version =", MODEL_VERSION)
    # 예시 DB 의 남성 실측자: profile 1(177.6cm, 81.5kg), 13(174.8cm, 106.9kg), 18·20·22(더미 회원)
    result = estimate("male", 175.0, 75.0, verbose=True)
    show("추정 치수 (male, 175.0cm, 75.0kg)", result)
    # 여성 실측자: profile 6, 11, 12, 19·21(더미 회원)
    result = estimate("female", 160.0, 60.0, verbose=True)
    show("추정 치수 (female, 160.0cm, 60.0kg)", result)
    print_note()
