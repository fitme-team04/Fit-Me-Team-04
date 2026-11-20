"""ZOZOTOWN 상품 페이지의 アイテムサイズ(実寸 cm: 着丈·身幅·肩幅·袖丈·ウエスト…) 표 수집 시도. 공식 API·데이터셋 없음.
1) zozo.jp 검색(Tシャツ, パンツ) → 상품 2~3개 → 원본 HTML 저장 + measurements.csv(item_id,name,brand,size,measure,value_cm).
   일반 브라우저 User-Agent 만 사용, 403/차단이면 access_log.json 에 그대로 기록하고 중단(우회 시도 없음).
2) 차단 시 참고용: tri-star/just-fit(라이선스 없음, 2013) 테스트 fixture 에 들어 있는 실제 2013년 ZOZOTOWN 상품 페이지 1건을 같은 파서로 정규화.
ZOZOTOWN 이용약관은 사이트 차단으로 원문 미확인 → 학생 PoC 내부 확인용으로만, 결과 재배포 금지. ZOZOMETRY(기업용 신체계측)도 공개 API 문서 없음.
API 키 불필요.
실행: python -m fetch.garment.zozotown_page
"""
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from .._common import SOURCES_DIR

NAME = "zozotown_page"
SITE = "https://zozo.jp"
QUERIES = ["Tシャツ", "パンツ"]
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml", "Accept-Language": "ja,en;q=0.8"}
JUSTFIT_SHA = "b80e188e14615468ec8b03c002f523dc842ae8b4"
FIXTURE_URL = (f"https://raw.githubusercontent.com/tri-star/just-fit/{JUSTFIT_SHA}"
               "/UrbanTheory/JustFit/Test/Engine/fixtures/ProductPageParser_Normal.html")
MEASURES = ["着丈", "身幅", "肩幅", "袖丈", "そで丈", "裄丈", "ゆき丈", "ウエスト", "ヒップ", "股上", "股下",
            "総丈", "わたり", "渡り", "裾幅", "すそ幅", "スカート丈", "胸囲", "バスト"]


def _get(url: str, log: list) -> bytes | None:
    """1회 요청. 실패하면 상태·서버·본문 일부를 log 에 남기고 None."""
    req = urllib.request.Request(url, headers=BROWSER)
    entry = {"url": url, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            entry.update(status=r.status, server=r.headers.get("Server"), bytes=len(body))
            log.append(entry)
            return body
    except urllib.error.HTTPError as e:
        body = _decode(e.read()[:2000])
        entry.update(status=e.code, server=e.headers.get("Server"),
                     geo_edge=e.headers.get("X-Geo-Location-Debug-Edge"),
                     body=re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()[:200])
    except urllib.error.URLError as e:
        entry.update(status=None, error=str(e.reason))
    log.append(entry)
    return None


def _decode(raw: bytes) -> str:
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
    enc = m.group(1).decode() if m else "utf-8"
    return raw.decode("cp932" if enc.lower() in ("shift_jis", "sjis", "x-sjis") else enc, "replace")


class _Tables(HTMLParser):
    """모든 <table> 을 [[셀 텍스트,...], ...] 로, og:title·canonical 도 수집."""
    def __init__(self):
        super().__init__()
        self.tables, self.meta, self._row, self._cell = [], {}, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self._row = []
        elif tag in ("th", "td") and self._row is not None:
            self._cell = []
        elif tag == "meta" and a.get("property") in ("og:title", "og:url"):
            self.meta[a["property"]] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.meta["canonical"] = a.get("href", "")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.tables[-1].append(self._row)
            self._row = None


def parse_product(html: str) -> list[dict]:
    """상품 HTML → measurements 행 리스트. 헤더 첫 칸이 サイズ 이고 실측 항목이 있는 표만 사용."""
    p = _Tables()
    p.feed(html)
    url = p.meta.get("canonical") or p.meta.get("og:url", "")
    m = re.search(r"gid=(\d+)|/goods(?:-sale)?/(\d+)", url)
    item_id = (m.group(1) or m.group(2)) if m else ""
    parts = p.meta.get("og:title", "").split(" / ")
    brand = " / ".join(parts[:-1]) if len(parts) > 1 else ""
    name = parts[-1] if parts else ""
    rows = []
    for t in p.tables:
        if not t or "サイズ" not in t[0][0] or not any(h in MEASURES for h in t[0][1:]):
            continue
        header = t[0]
        for r in t[1:]:
            for col, val in zip(header[1:], r[1:]):
                num = re.search(r"\d+(?:\.\d+)?", val)
                if num:
                    rows.append({"item_id": item_id, "name": name, "brand": brand, "size": r[0],
                                 "measure": col, "value_cm": float(num.group())})
    return rows


def fetch(dest: Path, fallback_fixture: bool = True) -> dict:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    info = {"name": NAME, "source": SITE, "version": datetime.now().strftime("%Y-%m-%d"),
            "license": "ZOZOTOWN 利用規約 — PoC 내부 확인용, 재배포 금지", "files": []}
    if any(dest.iterdir()):
        print(f"[{NAME}] skip: {dest} already has files")
        info["files"] = sorted(p.name for p in dest.rglob("*") if p.is_file())
        return info
    (dest / "raw").mkdir(exist_ok=True)
    log, rows, blocked = [], [], False

    # 1) robots.txt 확인 → 검색 → 상품 페이지 (쿼리당 상위 1~2개, 요청 사이 2초)
    robots = _get(f"{SITE}/robots.txt", log)
    if robots is None:
        blocked = True  # robots.txt 조차 거절 → 사이트가 이 클라이언트를 받지 않음, 중단
    elif re.search(rb"(?im)^Disallow:\s*/search", robots):
        blocked = True  # robots 가 검색 페이지 금지 → 중단
        (dest / "raw" / "robots.txt").write_bytes(robots)
    else:
        (dest / "raw" / "robots.txt").write_bytes(robots)
        urls = []
        for q in QUERIES:
            time.sleep(2)
            body = _get(f"{SITE}/search/?p_keyv={urllib.parse.quote(q)}", log)
            if body is None:
                blocked = True
                break
            found = re.findall(r'href="(/shop/[\w-]+/goods(?:-sale)?/\d+/)', _decode(body))
            urls += list(dict.fromkeys(found))[: 2 if q == QUERIES[0] else 1]
        for u in urls[:3]:
            time.sleep(2)
            body = _get(SITE + u, log)
            if body is None:
                blocked = True
                break
            gid = re.search(r"/(\d+)/$", u).group(1)
            (dest / "raw" / f"zozotown_{gid}.html").write_bytes(body)
            rows += parse_product(_decode(body))

    # 2) 차단 시: 2013년 실제 ZOZOTOWN 페이지(just-fit fixture) 1건으로 파서·표 구조만 확인
    if blocked and fallback_fixture:
        body = _get(FIXTURE_URL, log)
        if body is not None:
            (dest / "raw" / "justfit_fixture_2013_gid2189047.html").write_bytes(body)
            rows += parse_product(_decode(body))
            info["source"] += f" (blocked) + fixture {FIXTURE_URL}"

    (dest / "access_log.json").write_text(json.dumps({"blocked": blocked, "requests": log},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    with open(dest / "measurements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "name", "brand", "size", "measure", "value_cm"])
        w.writeheader()
        w.writerows(rows)
    print(f"[{NAME}] blocked={blocked} rows={len(rows)}")
    info["files"] = sorted(str(p.relative_to(dest)).replace("\\", "/") for p in dest.rglob("*") if p.is_file())
    return info


def sample(dest: Path, n: int = 3) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    dest = Path(dest)
    log = json.loads((dest / "access_log.json").read_text(encoding="utf-8"))
    for e in log["requests"]:
        print(f"  {e.get('status')} {e.get('server')} geo={e.get('geo_edge')} {e['url']} {e.get('body', '')[:80]}")
    with open(dest / "measurements.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_item = {}
    for r in rows:
        by_item.setdefault((r["item_id"], r["name"], r["brand"]), []).append(r)
    if not by_item:
        print("measurements.csv 비어 있음 — 실측표를 얻지 못함")
    for (iid, name, brand), rs in list(by_item.items())[:n]:
        print(f"item_id={iid}  {brand} | {name}")
        measures = list(dict.fromkeys(r["measure"] for r in rs))
        print("   size  " + "  ".join(f"{m:>5}" for m in measures))
        for size in dict.fromkeys(r["size"] for r in rs):
            vals = {r["measure"]: r["value_cm"] for r in rs if r["size"] == size}
            print(f"   {size:<6}" + "  ".join(f"{vals.get(m, '-'):>6}" for m in measures))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
