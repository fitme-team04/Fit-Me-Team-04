"""유니클로 일본 공식몰 리뷰 기반 사이즈 추천 데이터 (alviskwok/uniqlo_size_predictor).
GitHub 커밋 zip 을 받아 sources/uniqlo_size_predictor 에 푼다 (df.csv 약 7.9MB, item list.xlsx).
리뷰어 성별·연령대·키·체중·발 크기 → 구매 사이즈·별점, 상품 100개.
라이선스 없음 → PoC 전용 (상용 전환 시 교체). API 키 불필요.
실행: python -m fetch.fit.uniqlo_size_predictor
"""
import csv
import sys
from collections import Counter
from pathlib import Path

from .._common import SOURCES_DIR, github_zip, lock_version, read_xlsx

NAME = "uniqlo_size_predictor"
REPO = "alviskwok/uniqlo_size_predictor"
LICENSE = "없음 — PoC 전용"
UA = {"User-Agent": "fetch-uniqlo/1.0"}


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": f"https://github.com/{REPO}", "license": LICENSE}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} — 이미 파일 있음")
        info["version"] = lock_version(dest, NAME)
        info["files"] = sum(1 for p in dest.rglob("*") if p.is_file())
        return info
    sha, files = github_zip(REPO, dest, UA)
    info["version"] = f"commit {sha}"
    info["files"] = len(files)
    return info


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    path = dest / "df.csv"
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    print(f"== {NAME}: {path.name}")
    print("컬럼:", cols)
    print("행 수:", len(rows))
    items = {}
    for r in rows:
        items.setdefault(r["Item_Code"], (r["Item_Name"], r["Tags"].split(",")[0].strip()))
    print("서로 다른 상품 수 (Item_Code):", len(items))
    print("카테고리(Tags 첫 단어)별 상품 수:", dict(Counter(c for _, c in items.values()).most_common()))
    print("리뷰어 성별 분포:", dict(Counter(r["gender"] for r in rows)))
    print("전체 상품 (Item_Code / 이름 / 카테고리 / 리뷰 수):")
    per_item = Counter(r["Item_Code"] for r in rows)
    for code, (name, cat) in items.items():
        print(f"  {code} / {name} / {cat} / {per_item[code]}")
    print("컬럼별 빈 값 비율:")
    for c in cols:
        empty = sum(1 for r in rows if not r[c])
        print(f"  {c}: {empty / len(rows):.1%}")
    # 키·체중·나이가 모두 있는 실제 리뷰 n개 (파일 앞·중간·뒤에서 고르게)
    full = [r for r in rows if r["Height"] and r["Weight"] and r["AgeGroup"]]
    step = max(1, len(full) // n)
    print(f"키·체중·연령대가 모두 있는 행: {len(full)}개 — 그중 {n}개:")
    for r in full[::step][:n]:
        print("  ", dict(r))

    xlsx = dest / "item list.xlsx"
    if xlsx.exists():
        table = read_xlsx(xlsx)
        header = table[0]
        body = [t for t in table[1:] if t.get("A")]
        print(f"== {xlsx.name}: {len(body)}행, 헤더 {header}")
        print("  대상 성별(D)별 상품 수:", dict(Counter(t.get("D", "") for t in body)))
        diff = sum(1 for t in body if t.get("A", "") not in t.get("H", ""))
        print(f"  url 의 상품번호가 item code 와 다른 행: {diff}개 (I 열 '1' 표시: {sum(1 for t in body if t.get('I') == '1')}개)")
        for cells in body[:n]:
            print("  ", cells)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
