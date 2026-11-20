"""유니클로 일본 공식몰 리뷰 기반 사이즈 추천 데이터 (jackfai1993/Uniqlo_Size_Recommandation).
uniqlo_size_predictor 와 같은 팀 저장소. GitHub 커밋 zip 을 받아 sources/uniqlo_size_recommendation 에 푼다.
df.csv(Dept 열 없음), df_20220323ver.csv(Dept 포함), item list.xlsx 포함.
리뷰어 성별·연령대·키·체중·발 크기 → 구매 사이즈·별점.
라이선스 없음 → PoC 전용 (상용 전환 시 교체). API 키 불필요.
실행: python -m fetch.fit.uniqlo_size_recommendation
"""
import csv
import sys
from collections import Counter
from pathlib import Path

from .._common import SOURCES_DIR, github_zip, lock_version, read_xlsx

NAME = "uniqlo_size_recommendation"
REPO = "jackfai1993/Uniqlo_Size_Recommandation"
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


def _load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    path = dest / "df.csv"
    rows = _load_csv(path)
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

    # 2022-03-23 판과 비교
    old_path = dest / "df_20220323ver.csv"
    if old_path.exists():
        old = _load_csv(old_path)
        old_items = {r["Item_Code"] for r in old}
        print(f"== {old_path.name}: 컬럼 {list(old[0].keys())}")
        print(f"  행 수 {len(old)}, 상품 수 {len(old_items)}")
        print(f"  df.csv 에만 있는 상품: {sorted(set(items) - old_items)}")
        print(f"  {old_path.name} 에만 있는 상품: {sorted(old_items - set(items))}")
        old_ids = {r["id"] for r in old}
        print(f"  id 기준 공통 행: {sum(1 for r in rows if r['id'] in old_ids)}")

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
