"""여러 소스 스크립트가 똑같이 쓰던 작은 함수 모음."""
import io
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"  # <base>/sources


def get(url, headers, timeout=60):
    """GET 해서 본문 bytes 를 돌려준다."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        return r.read()


def api_get(url, headers, timeout=30):
    """GET 해서 (HTTP 상태, 본문 문자열). HTTP 오류도 예외 없이 돌려준다."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def download(url, out, headers, timeout=30):
    """큰 파일을 1 MB 씩 나눠 out 에 저장한다."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r, open(out, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def head_sha(repo, headers, timeout=60):
    """GitHub 저장소 기본 브랜치의 최신 커밋 sha."""
    branch = json.loads(get(f"https://api.github.com/repos/{repo}", headers, timeout))["default_branch"]
    return json.loads(get(f"https://api.github.com/repos/{repo}/commits/{branch}", headers, timeout))["sha"]


def github_zip(repo, dest, headers, timeout=60):
    """최신 커밋 zip 을 받아 맨 위 폴더를 떼고 dest 에 푼다. (sha, 상대 경로 목록) 반환."""
    sha = head_sha(repo, headers, timeout)
    z = zipfile.ZipFile(io.BytesIO(get(f"https://codeload.github.com/{repo}/zip/{sha}", headers, timeout)))
    files = []
    for info in z.infolist():
        rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""  # 맨 위 폴더 제거
        if not rel or info.is_dir() or ".." in Path(rel).parts:
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(z.read(info))
        files.append(rel)
    return sha, files


def lock_version(dest, name):
    """예전 init_sources.py 가 남긴 lock 에서 버전을 찾는다 (없으면 미기록)."""
    lock = dest.parent / "sources.lock.json"
    if lock.exists():
        rec = json.loads(lock.read_text(encoding="utf-8")).get(name)
        if rec:
            return rec.get("version", "미기록")
    return "기존 다운로드 (버전 미기록)"


def read_xlsx(path):
    """표준 라이브러리로 xlsx 첫 시트를 행 목록({열: 값})으로 읽는다."""
    m = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(m + "si"):
            shared.append("".join(t.text or "" for t in si.iter(m + "t")))
    rows = []
    for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(m + "row"):
        cells = {}
        for c in row.findall(m + "c"):
            v = c.find(m + "v")
            if c.get("t") == "s" and v is not None:
                val = shared[int(v.text)]
            elif c.get("t") == "inlineStr":
                val = "".join(t.text or "" for t in c.iter(m + "t"))
            else:
                val = v.text if v is not None else ""
            if val.endswith(".0") and val[:-2].isdigit():  # 439847.0 → 439847
                val = val[:-2]
            if val:
                cells[re.match(r"[A-Z]+", c.get("r")).group()] = val
        rows.append(cells)
    return rows
