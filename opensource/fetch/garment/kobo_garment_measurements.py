"""옷 치수 표준 데이터: 측정 지점(POM) 41개 정의, 사이즈표 5종(여 상의·여 하의·남 상의·남 하의·유니섹스, US/EU/UK/AU), 그레이드 규칙.
출처: GitHub kobo-labs-open-source/garment-measurements (기본 브랜치 HEAD 커밋 zip).
라이선스: MIT.
단위: cm. 가로 폭(*-width)은 옷을 펼쳐 놓고 잰 반폭(half-body) — 둘레로 쓰려면 ×2.
실행: python -m fetch.garment.kobo_garment_measurements
"""
import json
import sys
from pathlib import Path

from .._common import SOURCES_DIR, github_zip

NAME = "kobo_garment_measurements"
REPO = "kobo-labs-open-source/garment-measurements"
LICENSE = "MIT"
UA = {"User-Agent": "fetch-sources/1.0"}


def _files(dest):
    return [p for p in dest.rglob("*") if p.is_file()]


def fetch(dest: Path) -> dict:
    source = f"https://github.com/{REPO}"
    if dest.exists() and _files(dest):
        print(f"[건너뜀] {NAME} — 이미 있음 ({dest})")
        return {"name": NAME, "source": source, "version": "기존 파일 (건너뜀)",
                "license": LICENSE, "files": len(_files(dest))}
    sha, files = github_zip(REPO, dest, UA)
    count = len(files)
    print(f"[완료] {NAME} — commit {sha}, 파일 {count}개")
    return {"name": NAME, "source": source, "version": sha, "license": LICENSE, "files": count}


def sample(dest: Path, n: int = 3) -> None:
    data = dest / "data"

    # 1) 어떤 옷 종류가 있는지
    print("== 사이즈표 (옷 종류 / 지역 / 사이즈)")
    charts = {}
    for f in sorted((data / "size-charts").glob("*.json")):
        chart = json.loads(f.read_text(encoding="utf-8"))
        charts[f.stem] = chart
        regions = ", ".join(f"{r}({'/'.join(v['sizes'])})" for r, v in chart["regions"].items())
        print(f"  {chart['category']:<15} 단위={chart['unit']}  {regions}")
    rules = sorted(p.stem for p in (data / "grade-rules").glob("*.json"))
    print(f"  그레이드 규칙: {', '.join(rules)}")

    # 2) 남성 상의 US: 사이즈 × 측정 지점 (cm)
    us = charts["mens-tops"]["regions"]["US"]
    sizes = us["sizes"]
    print("\n== mens-tops / US (cm)")
    print(f"  {'측정 지점':<18}" + "".join(f"{s:>7}" for s in sizes))
    for point, values in us["measurements"].items():
        print(f"  {point:<18}" + "".join(f"{values[s]:>7}" for s in sizes))

    # 3) 측정 지점 정의 n개
    points = json.loads((data / "measurement-points.json").read_text(encoding="utf-8"))
    print(f"\n== 측정 지점 정의 (전체 {len(points)}개 중 {n}개)")
    for p in points[:n]:
        print(f"  [{p['id']}] {p['name']} ({p['code']})")
        print(f"     재는 법: {p['description']}")
        print(f"     별칭: {', '.join(p['aliases'])}")

    # 4) 반폭(half-body) 여부 — 원문 근거를 그대로 출력
    print("\n== 반폭 여부 근거")
    for line in (dest / "README.md").read_text(encoding="utf-8").splitlines():
        if "half-body" in line or "Chest width (half)" in line:
            print(f"  README: {line.strip()}")
    flat = [p["id"] for p in points if "laid flat" in p["description"]]
    print(f"  'laid flat'(펼쳐 놓고 잼) 정의: {', '.join(flat)}")
    print("  → 둘레를 대신하는 폭(chest/waist/hip/hem/thigh/bicep-width, sleeve/leg-opening 등)은 옷을 펼쳐 한 면을 잰 반폭이다.")
    print("     둘레 = 값 × 2 (예: US M chest-width "
          f"{us['measurements']['chest-width']['M']} cm → 옷 가슴둘레 약 {us['measurements']['chest-width']['M'] * 2} cm).")
    print("     across-shoulder·across-back 은 끝에서 끝까지 잰 직선 폭, 길이(*-length, inseam, rise)는 전체 길이 — ×2 하지 않는다.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
