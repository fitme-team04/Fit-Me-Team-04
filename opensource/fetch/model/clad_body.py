"""신체 치수 정의 코드: Anny / MHR 3D 몸 메시에서 ISO 8559-1 기준 치수 25개(키·가슴·허리·엉덩이·허벅지·인심 등)를 계산하는 Python 라이브러리.
출처: GitHub datar-psa/clad-body (기본 브랜치 HEAD 커밋 zip). 데이터 없이 코드만 있다.
라이선스: Apache-2.0.
sample() 은 라이브러리를 실행하지 않고 README 의 측정 정의 표(키·ISO 조항·정의)만 읽어 출력한다.
실행: python -m fetch.model.clad_body
"""
import sys
from pathlib import Path

from .._common import SOURCES_DIR, github_zip

NAME = "clad_body"
REPO = "datar-psa/clad-body"
LICENSE = "Apache-2.0"
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
    # README 표: | Contour | Key | Description | ISO | Type | Std | Region | Tier | Grp | Gar |
    # 표가 짧아 n 과 관계없이 측정 키 25개를 전부 출력한다
    rows = []
    for line in (dest / "README.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 10 and cells[1].startswith("`") and cells[1].endswith("`"):
            rows.append(cells)
    print(f"== clad-body 측정 키 {len(rows)}개 (README 표, ISO = ISO 8559-1 조항, -- = ISO 아님)")
    print(f"  {'key':<24}{'ISO':<8}{'type':<8}{'std':<9}{'tier':<6}{'garments':<10}definition")
    for c in rows:
        key, desc, iso, typ, std, tier, gar = c[1].strip("`"), c[2], c[3], c[4], c[5], c[7], c[9]
        print(f"  {key:<24}{iso:<8}{typ:<8}{std:<9}{tier:<6}{gar:<10}{desc}")
    print("  (garments 약어: T=tops, B=bottoms, D=dresses, O=outerwear, U=underwear)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
