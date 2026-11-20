"""유니클로 상품 2개의 사이즈 범위 JSON (Prisha-3012/Curate---HackMIT, cv/garments/).
크루넥 티셔츠·옥스퍼드 슬림 셔츠 — 사이즈(XS~XL)별 가슴·어깨 범위(cm), 상품 URL·이미지 URL.
기본 브랜치 HEAD 커밋을 고정해 raw.githubusercontent.com 에서 2개 파일만 받는다 → sources/uniqlo_garment_json.
라이선스 없음 → PoC 전용 (해커톤 작성자가 만든 값, 유니클로 공식 표 아님). API 키 불필요.
실행: python -m fetch.garment.uniqlo_garment_json
"""
import json
import sys
from pathlib import Path

from .._common import SOURCES_DIR, get, head_sha, lock_version

NAME = "uniqlo_garment_json"
REPO = "Prisha-3012/Curate---HackMIT"
FILES = ["cv/garments/uniqlo_crew_tee.json", "cv/garments/uniqlo_oxford_slim.json"]
LICENSE = "없음 — PoC 전용"
UA = {"User-Agent": "fetch-uniqlo/1.0"}


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": f"https://github.com/{REPO}/tree/HEAD/cv/garments", "license": LICENSE}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} — 이미 파일 있음")
        info["version"] = lock_version(dest, NAME)
        info["files"] = sorted(p.name for p in dest.iterdir() if p.is_file())
        return info
    sha = head_sha(REPO, UA)
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for f in FILES:
        out = dest / f.rsplit("/", 1)[1]
        out.write_bytes(get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{f}", UA))
        names.append(out.name)
    info["version"] = f"commit {sha}"
    info["files"] = names
    return info


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    for p in sorted(dest.glob("*.json"))[:n]:
        g = json.loads(p.read_text(encoding="utf-8"))
        print(f"== {p.name}: {g.get('name')} ({g.get('category')}, fit={g.get('fit')})")
        print("   설명:", g.get("description"))
        print("   상품:", g.get("product_url"))
        print("   이미지:", g.get("image_url"))
        for size, m in g.get("size_chart", {}).items():
            print(f"   {size:>3}: " + ", ".join(f"{k}={v[0]}~{v[1]}" for k, v in m.items()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
