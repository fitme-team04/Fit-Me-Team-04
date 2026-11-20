"""브랜드 사이즈표: 132개 브랜드가 공개한 사이즈표 496개를 한 장의 긴 표로 정리한 것 (사이즈 라벨별 가슴·허리·엉덩이 둘레 범위, cm).
출처: Hugging Face 데이터셋 fedorovvvv/oh-my-measure-brand-size-charts (리비전 sha 고정).
라이선스: "other" — 제공자가 숫자에 대한 권리를 주장하지도, 라이선스를 주지도 않음 (RIGHTS.txt). 브랜드 숫자는 각 브랜드 것, PoC 용도로만.
값은 대부분 신체 치수(몸 둘레) 범위이고 옷 실측(펼친 치수)이 아니다 — 표마다 출처 표 이름이 passports.json 에 있다.
실행: python -m fetch.garment.oh_my_measure
"""
import csv
import json
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

from .._common import SOURCES_DIR, get

NAME = "oh_my_measure"
DATASET = "fedorovvvv/oh-my-measure-brand-size-charts"
LICENSE = "other (제공자가 권리 주장·라이선스 부여 안 함, RIGHTS.txt)"
FILES = ["brand-grids.csv", "brands.csv", "passports.json", "datapackage.json",
         "RIGHTS.txt", "DATASET-README.txt", "README.md"]
UA = {"User-Agent": "fetch-sources/1.0"}

# 아시아 국가 코드 (ISO 3166-1 alpha-2). TR(튀르키예)은 대륙 경계라 따로 표시한다.
ASIA = {"JP", "KR", "CN", "TW", "HK", "MO", "MN", "SG", "TH", "VN", "ID", "MY", "PH",
        "KH", "LA", "MM", "IN", "PK", "BD", "LK", "NP", "KZ", "UZ", "AE", "SA", "IL"}


def fetch(dest: Path) -> dict:
    source = f"https://huggingface.co/datasets/{DATASET}"
    if dest.exists() and any(p.is_file() for p in dest.rglob("*")):
        print(f"[건너뜀] {NAME} — 이미 있음 ({dest})")
        return {"name": NAME, "source": source, "version": "기존 파일 (건너뜀)",
                "license": LICENSE, "files": sorted(p.name for p in dest.iterdir() if p.is_file())}
    rev = json.loads(get(f"https://huggingface.co/api/datasets/{DATASET}", UA))["sha"]
    dest.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        (dest / f).write_bytes(get(f"{source}/resolve/{rev}/{urllib.parse.quote(f)}", UA))
    print(f"[완료] {NAME} — revision {rev}, 파일 {len(FILES)}개")
    return {"name": NAME, "source": source, "version": rev, "license": LICENSE, "files": FILES}


def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _table_name(passport):
    # provenance.en 예: The “Body measurements” table — Oysho. ...
    text = passport["provenance"]["en"]
    return text.split("“", 1)[1].split("”", 1)[0] if "“" in text else text


def sample(dest: Path, n: int = 3) -> None:
    brands = _read_csv(dest / "brands.csv")
    rows = _read_csv(dest / "brand-grids.csv")
    passports = {p["grid_id"]: p for p in json.loads((dest / "passports.json").read_text(encoding="utf-8"))}

    grids = defaultdict(list)
    for r in rows:
        grids[r["grid_id"]].append(r)
    print(f"== 브랜드 {len(brands)}개, 사이즈표 {len(grids)}개, 행 {len(rows)}개")
    print(f"  cut 값: {sorted({r['cut'] for r in rows})}  (상의/하의 구분 열은 없음)")
    print(f"  system 값: {sorted({r['system'] for r in rows})}")
    print(f"  measure 값: {sorted({r['measure'] for r in rows})}")

    # 아시아 브랜드 전체
    asian = [b for b in brands if b["origin_code"] in ASIA]
    turkey = [b for b in brands if b["origin_code"] == "TR"]
    print(f"\n== 아시아 브랜드 {len(asian)}개")
    for b in asian:
        ids = sorted(g for g in grids if grids[g][0]["brand"] == b["brand"])
        print(f"  {b['origin_code']} {b['name']:<13} 그룹={b['group'] or '-':<15} 표 {len(ids)}개: {', '.join(ids)}")
    print(f"  (참고: TR 튀르키예 {len(turkey)}개 — {', '.join(b['name'] for b in turkey)})")

    # 아시아 브랜드 표 n개 (나라별로 남성 표 중 행이 가장 많은 것) 를 라벨 × 치수(범위) 로 펼쳐서 출력
    picks, seen = [], []
    for b in asian:
        if b["origin_code"] not in seen:
            seen.append(b["origin_code"])
    for code in seen:
        ids = [g for g in grids if grids[g][0]["brand"] in {b["brand"] for b in asian if b["origin_code"] == code}]
        mens = [g for g in ids if grids[g][0]["cut"] == "mens"] or ids
        best = max(sorted(mens), key=lambda g: len(grids[g]))
        if len(picks) < n:
            picks.append(best)
    for gid in picks:
        g = grids[gid]
        measures = [m for m in ("bust", "waist", "hip") if any(r["measure"] == m for r in g)]
        table = defaultdict(dict)
        labels = []
        for r in g:
            if r["label"] not in labels:
                labels.append(r["label"])
            table[r["label"]][r["measure"]] = f"{r['low_cm']}-{r['high_cm']}"
        p = passports.get(gid, {})
        print(f"\n== {gid}  ({g[0]['brand_name']}, system={g[0]['system']}, cut={g[0]['cut']}, 단위 cm)")
        print(f"  출처 표: “{_table_name(p)}”  {p['sources'][0]['url'] if p.get('sources') else ''}")
        print(f"  {'label':<8}{'alpha':<7}" + "".join(f"{m:>14}" for m in measures))
        for lab in labels:
            alpha = next((r["alpha"] for r in g if r["label"] == lab), "")
            print(f"  {lab:<8}{alpha:<7}" + "".join(f"{table[lab].get(m, '-'):>14}" for m in measures))

    # 신체 치수인지 옷 치수인지: passports 의 출처 표 이름으로 센다
    names = [_table_name(p) for p in passports.values()]
    body = [x for x in names if "body" in x.lower()]
    garment = [x for x in names if "garment" in x.lower()]
    print("\n== 몸 치수 vs 옷 치수 (passports.json 출처 표 이름 기준)")
    print(f"  전체 {len(names)}개 중 표 이름에 'Body' 포함 {len(body)}개, 'Garment' 포함 {len(garment)}개, 나머지 {len(names) - len(body) - len(garment)}개(브랜드 고유 표 이름)")
    print(f"  'Garment' 표: {sorted(g for g, p in passports.items() if 'garment' in _table_name(p).lower())}")
    one = [g for g, p in passports.items() if "one number per size" in p["provenance"]["en"]]
    print(f"  출처가 사이즈당 숫자 1개만 줘서 범위를 이웃 사이즈 중간까지로 만든 표: {len(one)}개")
    for line in (dest / "README.md").read_text(encoding="utf-8").splitlines():
        if "what chest girth" in line or "Girths in" in line:
            print(f"  README: {line.strip()}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
