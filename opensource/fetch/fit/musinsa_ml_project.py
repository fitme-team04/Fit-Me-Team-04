"""무신사 상의 실측 사이즈표 + 구매 후기(키·몸무게·고른 사이즈) 크롤링 데이터 (2023-06 수집, 학생 프로젝트)를 받는다.
출처: GitHub parkmy0420/ML_project (커밋 zip, codeload). data/ 에 상품별·사이즈별 총장·어깨너비·가슴단면(·소매길이) cm, 후기 결합본이 있다.
라이선스: 저장소에 LICENSE 없음 → 저작권 기본 보유, PoC 내부 확인용만. 무신사 공식 데이터가 아니라 무신사 사이트를 크롤링한 2차 자료.
상업 이용 불가로 취급. 키 불필요.
실행: python -m fetch.fit.musinsa_ml_project
"""
import csv
import io
import json
import sys
from pathlib import Path

from .._common import SOURCES_DIR, github_zip

NAME = "musinsa_ml_project"
REPO = "parkmy0420/ML_project"
UA = {"User-Agent": "poc-fetch/0.1"}
LICENSE = "없음 — PoC 전용 (무신사 크롤링 2차 자료)"


def fetch(dest: Path) -> dict:
    rec = {"name": NAME, "source": f"https://github.com/{REPO}", "license": LICENSE}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} — 이미 받음 ({dest})")
        rec.update({"version": "기존 파일", "files": sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())})
        return rec
    sha, files = github_zip(REPO, dest, UA, timeout=30)
    rec.update({"version": f"commit {sha}", "files": files})
    return rec


def _read_csv(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949"):  # 파일마다 인코딩이 다르다
        try:
            return list(csv.DictReader(io.StringIO(raw.decode(enc))))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"인코딩을 알 수 없음: {path}")


def sample(dest: Path, n: int = 3) -> None:
    rows = _read_csv(dest / "data" / "musinsa_top_product_v230612.csv")
    print("상품 실측 파일 컬럼:", ", ".join(rows[0].keys()), f"| {len(rows)}행")
    by_link = {}
    for r in rows:
        by_link.setdefault(r["링크"], []).append(r)
    print(f"상품 {len(by_link)}개 (사이즈별 1행, 단위 cm)")
    for link, sizes in list(by_link.items())[:n]:
        first = sizes[0]
        print(f"\n- 상품: {first['제품명']} | 브랜드: {first['브랜드']} | {link}")
        for s in sizes:
            vals = ", ".join(f"{k}={v}" for k, v in s.items() if k not in ("제품명", "브랜드", "링크"))
            print("   ", vals)

    reviews = _read_csv(dest / "data" / "data_final_final_final.csv")
    r = reviews[0]
    print(f"\n후기 결합본 data_final_final_final.csv {len(reviews)}행 — 구매자 몸 + 고른 사이즈 + 그 사이즈 실측 예:")
    print("   ", {k: r[k] for k in ("제품명", "사이즈", "총장", "어깨너비", "가슴단면", "유저성별", "키", "몸무게")})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(json.dumps(fetch(dest), ensure_ascii=False, indent=2))
    sample(dest)
