# 목적: AI 학습 표 만들기 — 1명 = 1행, 열 = 성별·나이·키·체중 + 치수 코드마다 1열 (없으면 빈칸) → CSV + 열별 채움 비율
# 누가 쓰나: AI
# 난이도: 심화 — 2개 표 JOIN + 선택 조건으로 읽고(_학습표.py) 파이썬으로 가로 펼치기·CSV
# 출력: 학습 표 CSV 10명·18열(기본정보+치수 12개, 빈칸=결측), 치수 열별 채움 비율 12행(50~100%), bodym 3명 표
# db/query/train/01_wide_by_profile.sql 과 같은 행·열 (실측 measured 만, 추정값 제외)
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/04_학습용_데이터표_만들기.py            (CSV 를 화면에 출력)
#       .venv/bin/python db/예시_코드/ai/2_심화/04_학습용_데이터표_만들기.py --save     (out/ai/dataset.csv 로도 저장)
import csv
import io
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show, save_text
from _학습표 import BASE_COLUMNS, MEASURE_COLUMNS, load_rows     # 학습 표 읽기 (예시_코드/_학습표.py)


# 목적: 표 → CSV 글자 (None 은 빈칸)
def to_csv(table):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    columns = BASE_COLUMNS + MEASURE_COLUMNS
    writer.writerow(columns)
    for row in table:
        cells = []
        for col in columns:
            if row[col] is None:
                cells.append("")
            else:
                cells.append(row[col])
        writer.writerow(cells)
    return buffer.getvalue()


# 목적: 치수 열마다 값이 있는 사람 수·비율 (학습에 쓸 수 있는 열 고르기용)
def coverage(table):
    result = []
    for code in MEASURE_COLUMNS:
        filled = 0
        for row in table:
            if row[code] is not None:
                filled += 1
        pct = 0.0
        if len(table) > 0:
            pct = round(filled * 100.0 / len(table), 1)
        result.append({"measure_code": code, "filled_tally": filled, "total_tally": len(table), "filled_pct": pct})
    return result


if __name__ == "__main__":
    table = load_rows()
    text = to_csv(table)
    print("■ 학습 표 CSV (" + str(len(table)) + "명)")
    print(text, end="")
    if "--save" in sys.argv:
        path = save_text("ai/dataset.csv", text)
        print("  → 저장: " + str(path))
    show("치수 열별 채움 비율", coverage(table))
    show("출처 하나만 (source_name = bodym)", load_rows("bodym"))
