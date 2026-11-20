"""NHANES (미국 국민건강영양조사 1999~2017, 2021) 참가자 단위 통합본을 받는다.
출처: Hugging Face gracemyu/nhanes-merged (OpenFIM-Bench 파이프라인 산출물), 리비전 고정
파일: merged_deduped.parquet (약 283MB, 113,386행 x 14,066열) + README.md
라이선스: CC0-1.0 (HF 카드 표기, 원자료는 미국 연방정부 공공 저작물)
열 이름은 {원본표}_{원본변수} 소문자 (예: bmx_bmxht = BMX 표의 BMXHT = 키 cm)
sample(): 로컬 parquet + pyarrow 가 있으면 그걸 읽고, 없으면 같은 변수를 CDC 원본 XPT 에서 읽는다
          (HF rows API 는 열이 1,000개 넘는 데이터셋을 지원하지 않아 이 데이터셋에선 쓸 수 없음)
실행: python -m fetch.body.nhanes
"""
import json
import struct
import sys
import urllib.parse
from pathlib import Path

from .._common import SOURCES_DIR, download, get

NAME = "nhanes"
DATASET = "gracemyu/nhanes-merged"
REVISION = "2069b6643803fdf1a110b3c632dfc0fe3bb0b08d"  # 2026-11-05 확인한 main 커밋
FILES = ["README.md", "merged_deduped.parquet"]
UA = {"User-Agent": "fetch-nhanes/1.0"}

# 보여 줄 열 (단위는 NHANES 코드북 기준)
COLUMNS = [
    ("demo_riagendr", "성별 (1=남, 2=여)"),
    ("demo_ridageyr", "나이 (세)"),
    ("bmx_bmxht", "키 (cm)"),
    ("bmx_bmxwt", "체중 (kg)"),
    ("bmx_bmxarml", "위팔 길이 어깨~팔꿈치 (cm)"),
    ("bmx_bmxleg", "윗다리 길이 (cm)"),
    ("bmx_bmxwaist", "허리둘레 (cm)"),
    ("bmx_bmxhip", "엉덩이둘레 (cm)"),
    ("bmx_bmxarmc", "위팔 둘레 (cm)"),
    ("bmx_bmxthicr", "허벅지 둘레 (cm)"),
    ("bmx_bmxcalf", "종아리 둘레 (cm)"),
    ("bix_bidfat", "BIA 체지방량 (kg)"),
    ("bix_bidpfat", "BIA 체지방률 (%)"),
    ("bix_bidffm", "BIA 제지방량 (kg)"),
]
# 근육·제지방 관련 DXA 열 (merged 파일 스키마에 있는 것; 전신 DXA 'dxx' 는 multi_row/dxx.parquet 에 따로 있음)
LEAN_COLUMNS = [
    "dxx_2_dx2tole", "dxx_2_dx2toli", "dxx_2_dx2lale", "dxx_2_dx2rale", "dxx_2_dx2llle",
    "dxx_2_dx2rlle", "dxx_2_dx2trle", "dxxag_dxxanlm", "dxxag_dxxgylm",
]
# parquet 이 없을 때 쓰는 CDC 원본: (주기 시작연도, 접미사, 표 목록, 값이 꼭 있어야 하는 열)
# BIA 체지방은 1999~2004 에만, 엉덩이둘레는 2011 이후에만 있어 한 주기로는 다 못 보여 준다
CDC_CYCLES = [("2003", "C", ["DEMO", "BMX", "BIX"], "bix_bidpfat"),
              ("2017", "J", ["DEMO", "BMX", "DXXAG"], "dxxag_dxxanlm")]


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": f"https://huggingface.co/datasets/{DATASET}",
            "version": f"revision {REVISION}", "license": "CC0-1.0", "files": []}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} — 이미 파일 있음: {dest}")
        info["files"] = [{"path": p.name, "bytes": p.stat().st_size} for p in sorted(dest.iterdir()) if p.is_file()]
        return info
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{urllib.parse.quote(name)}"
        out = dest / name
        part = dest / (name + ".part")
        # 283MB 라 메모리에 다 올리지 않고 1MB 씩 저장한 뒤 이름을 바꾼다
        download(url, part, UA, timeout=120)
        part.replace(out)
        info["files"].append({"path": name, "bytes": out.stat().st_size})
        print(f"[받음] {name} ({out.stat().st_size:,} bytes)")
    return info


# ---------- parquet (pyarrow 있을 때만) ----------
def rows_from_parquet(path: Path, cols: list, n: int):
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("(pyarrow 없음 → CDC 원본으로 대신 확인. 로컬 parquet 을 읽으려면 pip install pyarrow)")
        return None
    names = set(pq.ParquetFile(path).schema_arrow.names)
    table = pq.read_table(path, columns=[c for c in cols if c in names])
    out = []
    for row in table.to_pylist():
        if row.get("bmx_bmxht") is not None and row.get("bmx_bmxwaist") is not None and (row.get("demo_ridageyr") or 0) >= 20:
            out.append(row)
            if len(out) >= n:
                break
    return out


# ---------- CDC 원본 SAS XPT (v5) 읽기, 표준 라이브러리만 ----------
def ibm_to_float(b: bytes):
    if b[0] in b"._ABCDEFGHIJKLMNOPQRSTUVWXYZ" and not any(b[1:]):
        return None  # SAS 결측값
    b = b.ljust(8, b"\0")
    sign = -1 if b[0] & 0x80 else 1
    exponent = (b[0] & 0x7F) - 64
    mantissa = int.from_bytes(b[1:8], "big") / float(1 << 56)
    return sign * mantissa * 16.0 ** exponent


def read_xpt(data: bytes) -> list:
    head = data.find(b"NAMESTR HEADER RECORD") - 20
    nvars = int(data[head + 54:head + 58])
    variables, pos = [], head + 80
    for _ in range(nvars):
        ns = data[pos:pos + 140]
        ntype, length = struct.unpack(">h", ns[0:2])[0], struct.unpack(">h", ns[4:6])[0]
        name = ns[8:16].decode("ascii").strip()
        offset = struct.unpack(">i", ns[84:88])[0]
        variables.append((name, ntype, length, offset))
        pos += 140
    obs = data.find(b"OBS     HEADER RECORD", pos) - 20 + 80
    rowlen = sum(v[2] for v in variables)
    rows = []
    for start in range(obs, len(data) - rowlen + 1, rowlen):
        raw = data[start:start + rowlen]
        if raw.strip(b" ") == b"":
            break  # 끝의 공백 채움
        row = {}
        for name, ntype, length, offset in variables:
            cell = raw[offset:offset + length]
            row[name.lower()] = ibm_to_float(cell) if ntype == 1 else cell.decode("latin-1").strip()
        rows.append(row)
    return rows


def rows_from_cdc(n: int) -> list:
    out = []
    for i, (year, suffix, tables, required) in enumerate(CDC_CYCLES):
        want = (n + 1) // 2 if i == 0 else n - len(out)
        if want <= 0:
            break
        joined = None
        for t in tables:
            url = f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{t}_{suffix}.xpt"
            by_seqn = {r["seqn"]: r for r in read_xpt(get(url, UA, timeout=120))}
            print(f"  CDC {t}_{suffix}.xpt: {len(by_seqn):,}명")
            if joined is None:
                joined = {s: {"seqn": s, "year": f"{year}-{int(year) + 1}"} for s in by_seqn}
            for s, r in by_seqn.items():
                if s in joined:
                    joined[s].update({f"{t.lower()}_{k}": v for k, v in r.items() if k != "seqn"})
        for row in joined.values():
            if (row.get("demo_ridageyr") or 0) >= 20 and row.get("bmx_bmxht") and row.get("bmx_bmxwaist") and row.get(required) is not None:
                out.append(row)
                if sum(1 for r in out if r["year"].startswith(year)) >= want:
                    break
    return out


def check_columns(cols: list) -> None:
    url = "https://datasets-server.huggingface.co/info?dataset=" + urllib.parse.quote(DATASET, safe="")
    features = json.loads(get(url, UA, timeout=120))["dataset_info"]["default"]["features"]
    missing = [c for c in cols if c not in features]
    print(f"HF 스키마 확인 (datasets-server /info): 열 {len(features):,}개, 아래 열 {len(cols) - len(missing)}/{len(cols)}개 존재"
          + (f", 없음: {missing}" if missing else ""))


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    cols = ["seqn", "year"] + [c for c, _ in COLUMNS] + LEAN_COLUMNS
    parquet = dest / "merged_deduped.parquet"
    rows = rows_from_parquet(parquet, cols, n) if parquet.exists() else None
    if rows is None:
        check_columns([c for c in cols if c not in ("seqn", "year")])
        print("실제 행: HF 통합본이 합친 CDC 원본 XPT 를 메모리로 읽음 (같은 변수, 열 이름은 표_변수 소문자로 맞춤)")
        rows = rows_from_cdc(n)
    for row in rows:
        print(f"\n--- seqn {row.get('seqn'):.0f}, 주기 {row.get('year')} ---")
        for col, label in COLUMNS:
            v = row.get(col)
            print(f"  {col:16s} {('null' if v is None else f'{v:g}'):>8s}  {label}")
        lean = {c: row.get(c) for c in LEAN_COLUMNS if row.get(c) is not None}
        print(f"  DXA 제지방(근육) 열: {lean if lean else '이 출처/사람에선 없음 (null)'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    # 283MB 를 받는다. 받기 전에 sample() 만 보려면 fetch 줄을 주석 처리
    fetch(dest)
    sample(dest)
