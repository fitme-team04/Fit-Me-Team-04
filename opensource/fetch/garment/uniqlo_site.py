"""유니클로 공식 사이트(uniqlo.com)가 브라우저에 공개적으로 내려주는 사이즈 정보를 받는다.
- 일본 체형 사이즈표 이미지 2장(남/여, image.uniqlo.com) → 표 값은 사람이 이미지에서 옮겨 적어 BODY_CHART_JP 에 넣음
- 사이트 자체가 쓰는 Commerce API v5: 상품 검색(us/jp/kr) → 같은 상품들의 /products/size-charts
  (상품 실측 sizeChart = 옷 기준, bodyMeasurements = 체형 기준, 사이즈별 cm/inch)
- 결과: sources/uniqlo_site/raw/*(원본) + size_charts.csv(정규화)
약관: 오픈 라이선스 아님(UNIQLO/Fast Retailing 사이트 이용약관 적용). 학생 PoC 내부 참고용으로만 쓰고 재배포하지 않는다.
실행: python -m fetch.garment.uniqlo_site
"""
import csv
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .._common import SOURCES_DIR

NAME = "uniqlo_site"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
IMG = "https://image.uniqlo.com/UQ/ST3/jp/imagesother/sizechart/graph_bodysize_uq_{}.jpg"

# (국가, 언어, 검색어, Accept-Language)
COUNTRIES = [
    ("us", "en", "t-shirt", "en-US,en;q=0.9"),
    ("jp", "ja", "ティーシャツ", "ja-JP,ja;q=0.9"),
    ("kr", "ko", "티셔츠", "ko-KR,ko;q=0.9"),
]
SEARCH_LIMIT = 5
# 검색 결과에 없더라도 꼭 넣을 상품 (오픈소스 저장소들이 참조한 크루넥 T, 흰색 00)
EXTRA_IDS = {"us": ["E422992-000-00"], "jp": [], "kr": []}

CSV_COLS = ["source_url", "garment_type", "gender", "size", "measure",
            "value_or_range", "unit", "basis", "product_id", "extracted"]

# 일본 체형 사이즈표 이미지(graph_bodysize_uq_m/w.jpg)를 눈으로 옮겨 적은 값. 단위 cm. 병합 셀은 해당 사이즈 전부에 같은 값.
# (garment_type, gender, measure, {size: value})
BODY_CHART_JP = [
    ("tops(공통 체형표)", "MEN", "height", {"XS": "155-165", "S": "155-165", "M": "165-175", "L": "175-185",
                                         "XL": "175-185", "XXL": "175-185", "3XL": "175-185", "4XL": "175-185"}),
    ("tops(공통 체형표)", "MEN", "neck", {"XS": "-37", "S": "-38", "M": "-40", "L": "-42",
                                       "XL": "-44", "XXL": "-46", "3XL": "-48.5", "4XL": "-51"}),
    ("tops(공통 체형표)", "MEN", "yuki(center-back to wrist)", {"XS": "-78.5", "S": "-80.5", "M": "-83", "L": "-85.5",
                                                             "XL": "-88", "XXL": "-90", "3XL": "-91.5", "4XL": "-93"}),
    ("tops(공통 체형표)", "MEN", "chest", {"XS": "78-84", "S": "80-88", "M": "88-96", "L": "96-104",
                                        "XL": "104-112", "XXL": "112-120", "3XL": "120-128", "4XL": "128-136"}),
    ("tops(공통 체형표)", "MEN", "waist", {"XS": "66-72", "S": "68-76", "M": "76-84", "L": "84-92",
                                        "XL": "92-100", "XXL": "100-108", "3XL": "108-116", "4XL": "116-124"}),
    ("bottoms(인치 사이즈)", "MEN", "waist", {"27": "68", "28": "70", "29": "73", "30": "76", "31": "79", "32": "82",
                                          "33": "84", "34": "86.5", "35": "88", "36": "91", "37": "94", "38": "95",
                                          "40": "100", "42": "105", "44": "110", "46": "115", "48": "120"}),
    ("tops(공통 체형표)", "WOMEN", "height", {"XS": "149-156", "S": "153-160", "M": "153-160", "L": "159-166",
                                           "XL": "159-166", "XXL": "159-166", "3XL": "159-166"}),
    ("tops(공통 체형표)", "WOMEN", "bust", {"XS": "74-80", "S": "77-83", "M": "80-86", "L": "86-92",
                                         "XL": "92-98", "XXL": "98-104", "3XL": "104-110"}),
    ("tops(공통 체형표)", "WOMEN", "waist", {"XS": "57-63", "S": "60-66", "M": "63-69", "L": "69-75",
                                          "XL": "75-81", "XXL": "81-87", "3XL": "87-93"}),
    ("tops(공통 체형표)", "WOMEN", "hip", {"XS": "82-88", "S": "85-91", "M": "88-94", "L": "94-100",
                                        "XL": "100-106", "XXL": "106-112", "3XL": "112-118"}),
    ("tops(공통 체형표)", "WOMEN", "jp_gousu(号数)", {"XS": "5", "S": "7", "M": "9", "L": "11",
                                                  "XL": "13", "XXL": "15", "3XL": "17"}),
    ("tights", "WOMEN", "height", {"M/L": "150-165", "L/XL": "155-170"}),
    ("tights", "WOMEN", "hip", {"M/L": "85-98", "L/XL": "90-103"}),
    ("bottoms(인치 사이즈)", "WOMEN", "waist", {"21": "53.5", "22": "56", "23": "58.5", "24": "61", "25": "63.5",
                                            "26": "66", "27": "68.5", "28": "71", "29": "73.5", "30": "76",
                                            "31": "78.5", "32": "81", "33": "84", "34": "86.5", "35": "89",
                                            "36": "91.5"}),
    ("bottoms(cm 사이즈)", "WOMEN", "hip", {"58": "85", "61": "88", "64": "91", "67": "94", "70": "97",
                                         "73": "99", "76": "101", "79": "103"}),
    ("bra", "WOMEN", "underbust", {"65": "62.5-67.5", "70": "67.5-72.5", "75": "72.5-77.5",
                                   "80": "77.5-82.5", "85": "82.5-87.5", "90": "87.5-92.5"}),
    ("bra", "WOMEN", "cup(top-under)", {"AA": "7.5", "A": "10", "B": "12.5", "C": "15",
                                        "D": "17.5", "E": "20", "F": "22.5"}),
]


def _get(url, path, log, headers=None, lang="en-US,en;q=0.9"):
    """요청 1회(타임아웃 20초, 이후 1초 쉼). 성공하면 path 에 저장하고 True."""
    h = {"User-Agent": UA, "Accept-Language": lang, "Accept": "*/*", "Accept-Encoding": "gzip"}
    h.update(headers or {})
    rec = {"url": url, "file": path.name}
    ok = False
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            path.write_bytes(body)
            rec.update(status=r.status, bytes=len(body))
            ok = True
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, head=e.read()[:200].decode("utf-8", "replace"))
    except Exception as e:  # 타임아웃·연결 실패
        rec.update(status=None, error=f"{type(e).__name__}: {e}", secs=round(time.time() - t0, 1))
    log.append(rec)
    print("  GET", rec.get("status"), url)
    time.sleep(1)
    return ok


def _api_headers(cc):
    return {"x-fr-clientid": f"uq.{cc}.web-spa", "Accept": "application/json"}


def _search_url(cc, lang, q):
    return (f"https://www.uniqlo.com/{cc}/api/commerce/v5/{lang}/products"
            f"?q={urllib.parse.quote(q)}&limit={SEARCH_LIMIT}")


def _size_chart_url(cc, lang, ids):
    return (f"https://www.uniqlo.com/{cc}/api/commerce/v5/{lang}/products/size-charts"
            f"?productIdsWithColorCode={','.join(ids)}&includeBodyMeasurements=true&simpleSizeChart=false")


def _load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _ids_from_search(search):
    ids = []
    for it in (search or {}).get("result", {}).get("items", []):
        color = it.get("representativeColorDisplayCode")
        if not color and it.get("colors"):
            color = it["colors"][0].get("displayCode")
        ids.append(f"{it['productId']}-{color or '00'}")
    return ids


def _build_csv(dest, raw):
    rows = []
    # 1) 일본 체형 사이즈표 이미지 (옮겨 적은 값, 체형 기준)
    for gtype, gender, measure, values in BODY_CHART_JP:
        src = IMG.format("m" if gender == "MEN" else "w")
        for size, v in values.items():
            rows.append([src, gtype, gender, size, measure, v, "cm", "body", "", "manual_transcription_from_image"])
    # 2) Commerce API size-charts (옷 실측 + 체형)
    seen = set()
    for cc, lang, _q, _al in COUNTRIES:
        names = {}
        for it in (_load_json(raw / f"api_{cc}_search.json") or {}).get("result", {}).get("items", []):
            names[it["productId"]] = (it.get("name", ""), it.get("genderName", ""))
        for f in sorted(raw.glob(f"api_{cc}_size-charts*.json")):
            data = _load_json(f) or {}
            for prod in data.get("result", []) or []:
                pid = prod.get("productId", "")
                if (cc, pid) in seen:
                    continue
                seen.add((cc, pid))
                name, gender = names.get(pid, ("", ""))
                src = (f"https://www.uniqlo.com/{cc}/api/commerce/v5/{lang}/products/size-charts"
                       f"?productIdsWithColorCode={pid}-{prod.get('colorCode', '00')}")
                for key, basis in (("sizeChart", "garment"), ("bodyMeasurements", "body")):
                    for s in prod.get(key) or []:
                        for part in s.get("sizeParts", []):
                            ms = part.get("measurements") or []
                            m = next((x for x in ms if x.get("unit") == "cm"), ms[0] if ms else None)
                            if not m:
                                continue
                            rows.append([src, name or pid, gender, s.get("name", ""), part.get("code", ""),
                                         m.get("value", "").replace(" ", ""), m.get("unit", ""), basis,
                                         f"{cc}:{pid}", "api_json"])
    out = dest / "size_charts.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        w.writerows(rows)
    return out, len(rows)


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    raw = dest / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    log, downloaded = [], 0

    def need(name):
        return not (raw / name).exists()

    # 1) 체형 사이즈표 이미지 + robots.txt (이용 규칙 기록용)
    for g in ("m", "w"):
        fn = f"graph_bodysize_uq_{g}.jpg"
        if need(fn):
            downloaded += _get(IMG.format(g), raw / fn, log, lang="ja-JP,ja;q=0.9")
    if need("robots.txt"):
        downloaded += _get("https://www.uniqlo.com/robots.txt", raw / "robots.txt", log)

    # 2) 국가별 검색 1회 → 같은 상품들의 size-charts 1회
    for cc, lang, q, al in COUNTRIES:
        sfn = f"api_{cc}_search.json"
        if need(sfn):
            downloaded += _get(_search_url(cc, lang, q), raw / sfn, log, _api_headers(cc), al)
        cfn = f"api_{cc}_size-charts.json"
        if need(cfn) and (raw / sfn).exists():
            ids = _ids_from_search(_load_json(raw / sfn)) + EXTRA_IDS.get(cc, [])
            ids = list(dict.fromkeys(ids))
            if ids:
                downloaded += _get(_size_chart_url(cc, lang, ids), raw / cfn, log, _api_headers(cc), al)

    if log:
        with open(dest / "fetch_log.jsonl", "a", encoding="utf-8") as fh:
            for rec in log:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    out, n = _build_csv(dest, raw)
    failed = [r for r in log if r.get("status") != 200]
    status = "cached" if not log else ("ok" if not failed else f"partial ({len(failed)} failed)")
    return {
        "name": NAME,
        "source": "https://www.uniqlo.com/{country}/api/commerce/v5/{lang}/products/size-charts ; " + IMG.format("m|w"),
        "version": time.strftime("%Y-%m-%d") + " (fetched; Commerce API v5)",
        "license": "No open license - UNIQLO site terms apply; PoC internal reference only, do not redistribute",
        "files": sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()),
        "status": f"{status}; downloaded={downloaded}; csv_rows={n}",
    }


def sample(dest: Path, n: int = 3) -> None:
    p = Path(dest) / "size_charts.csv"
    if not p.exists():
        print("size_charts.csv 없음 - fetch() 먼저 실행")
        return
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    # 상품(product_id = "국가:상품번호")별로 묶음
    prods = {}
    for r in rows:
        if r["extracted"] == "api_json":
            prods.setdefault(r["product_id"], []).append(r)
    # 나라마다 첫 상품 1개씩 먼저 고르고, 모자라면 나머지에서 채움
    chosen = []
    for cc, _lang, _q, _al in COUNTRIES:
        for k in prods:
            if k.startswith(cc + ":"):
                chosen.append(k)
                break
    for k in prods:
        if k not in chosen:
            chosen.append(k)
    for k in chosen[:n]:
        rs = prods[k]
        print(f"\n[{k}] {rs[0]['garment_type']} ({rs[0]['gender']})  {rs[0]['source_url']}")
        for basis in ("garment", "body"):
            sizes = list(dict.fromkeys(r["size"] for r in rs if r["basis"] == basis))
            for s in sizes:
                parts = ", ".join(f"{r['measure']}={r['value_or_range']}{r['unit']}"
                                  for r in rs if r["basis"] == basis and r["size"] == s)
                print(f"  {basis:7s} {s:5s} {parts}")
    body = [r for r in rows if r["extracted"] != "api_json"]
    print(f"\n[JP 체형표 이미지 옮겨 적음] {len(body)}행, 예: "
          + "; ".join(f"{r['gender']} {r['size']} {r['measure']}={r['value_or_range']}cm" for r in body[:4]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    d = SOURCES_DIR / NAME
    info = fetch(d)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    sample(d)
