"""Amazon BodyM 데이터셋을 받는다 (공개 S3 버킷 amazon-bodym, us-west-2, 계정 불필요).
내용: 피험자별 키·체중·성별(hwg_metadata.csv) + 14개 신체 치수(measurements.csv, cm), 정면·측면 실루엣 이미지
기본은 CSV 만 받는다 (약 1.5MB, 9개). with_images=True 면 실루엣까지 (약 90MB, 약 18,000개)
라이선스: CC BY-NC 4.0 (AWS Open Data 레지스트리 표기, 비상업 전용)
실행: python -m fetch.body.bodym
"""
import csv
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from .._common import SOURCES_DIR, get

NAME = "bodym"
HOST = "https://amazon-bodym.s3.us-west-2.amazonaws.com"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
UA = {"User-Agent": "fetch-bodym/1.0"}


def list_keys() -> list:
    keys, token = [], None
    while True:
        q = "?list-type=2&max-keys=1000"
        if token:
            q += "&continuation-token=" + urllib.parse.quote(token)
        x = ET.fromstring(get(HOST + "/" + q, UA, timeout=120))
        keys += [c.find(NS + "Key").text for c in x.findall(NS + "Contents")]
        nxt = x.find(NS + "NextContinuationToken")
        token = nxt.text if nxt is not None else None
        if not token:
            return keys


def fetch(dest: Path, with_images: bool = False) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": "s3://amazon-bodym (us-west-2)", "version": "",
            "license": "CC BY-NC 4.0 (비상업 전용)", "files": []}
    have = [p for p in dest.rglob("*") if p.is_file()] if dest.exists() else []
    has_images = any(not p.name.lower().endswith(".csv") for p in have)
    if have and (has_images or not with_images):
        print(f"[건너뜀] {NAME} — 이미 파일 {len(have)}개 있음: {dest}")
        info["version"] = f"로컬 {len(have)}개"
        info["files"] = [str(p.relative_to(dest)).replace("\\", "/") for p in have if p.suffix.lower() == ".csv"]
        return info
    keys = list_keys()
    want = [k for k in keys if not k.endswith("/") and (with_images or k.lower().endswith(".csv"))]
    for i, k in enumerate(want, 1):
        out = dest / k
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(get(HOST + "/" + urllib.parse.quote(k), UA, timeout=120))
        if i % 500 == 0:
            print(f"    {i}/{len(want)}")
    info["version"] = f"버킷 객체 {len(keys)}개 중 {len(want)}개 ({'csv + 실루엣' if with_images else 'csv 만'})"
    info["files"] = [k for k in want if k.lower().endswith(".csv")]
    print(f"[받음] {NAME} — {info['version']}")
    return info


def read_csv(path: Path) -> list:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    print("CSV 목록:")
    for p in sorted(dest.rglob("*.csv")):
        rows = read_csv(p)
        print(f"  {str(p.relative_to(dest)):34s} {len(rows):6,}행  열: {', '.join(rows[0].keys()) if rows else '-'}")

    split = dest / "train"
    meta = {r["subject_id"]: r for r in read_csv(split / "hwg_metadata.csv")}
    meas = read_csv(split / "measurements.csv")
    print(f"\ntrain: 치수 {len(meas):,}명, 메타 {len(meta):,}명 — subject_id 로 결합")
    shown = 0
    for m in meas:
        h = meta.get(m["subject_id"])
        if h is None:
            continue
        print(f"\n--- {h['gender']} 키 {h['height_cm']} cm, 체중 {h['weight_kg']} kg (subject {m['subject_id'][:12]}…) ---")
        for col, val in m.items():
            if col != "subject_id":
                print(f"  {col:20s} {float(val):6.1f} cm")
        shown += 1
        if shown >= n:
            break


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    fetch(dest)
    sample(dest)
