"""받은 데이터 목록(manifest) = sources/sources.lock.json. 사람이 쓰지 않고 코드가 잰다 (DVC 의 dvc.lock 방식).
소스마다: source, version(commit/revision), license, files(파일 수), bytes(합계), sha256(폴더 해시), fetched_at, measured_at
- 자동 기록: `from fetch import SOURCES` 로 부른 fetch(dest) 가 끝나면 그 소스 줄을 갱신한다.
- 다시 재고 표 보기: python -m fetch.manifest   (sources/ 의 폴더를 다시 잰다, 네트워크 안 씀)
sha256 은 파일별 sha256 과 상대 경로를 정렬해 한 번 더 해시한 값 — 내용이 바뀌면 값이 바뀐다.
"""
import functools
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ._common import SOURCES_DIR

LOCK = SOURCES_DIR / "sources.lock.json"
# fetch 가 '이미 있어서 건너뜀' 일 때 돌려주는 version 문구 → 이전 기록의 version 을 유지
PLACEHOLDER = ("기존", "로컬", "건너뜀", "미기록")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def measure(dest):
    """폴더의 파일 수, 바이트 합계, 폴더 해시."""
    files = sorted(p for p in Path(dest).rglob("*") if p.is_file())
    folder = hashlib.sha256()
    total = 0
    for p in files:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        folder.update(f"{h.hexdigest()}  {p.relative_to(dest).as_posix()}\n".encode("utf-8"))
        total += p.stat().st_size
    newest = max((p.stat().st_mtime for p in files), default=0)
    return {"files": len(files), "bytes": total, "sha256": folder.hexdigest(), "newest": newest}


def load():
    return json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}


def save(lock):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(dict(sorted(lock.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update(rec, dest, use=""):
    """fetch() 결과 rec 과 폴더 측정값을 lock 에 합쳐 저장한다. 받은 파일이 없으면(needs_key 등) 그대로 둔다."""
    dest = Path(dest)
    if not dest.is_dir() or not any(dest.iterdir()):
        return
    lock = load()
    old = lock.get(rec["name"], {})
    m = measure(dest)
    same = old.get("sha256") == m["sha256"]
    version = str(rec.get("version") or "")
    if old.get("version") and (same or not version or any(w in version for w in PLACEHOLDER)):
        version = old["version"]  # 내용이 그대로거나 '건너뜀' 기록이면 처음 받을 때의 버전 유지
    if not version or any(w in version for w in PLACEHOLDER):
        version = "미기록 (예전에 받음, 다시 받으면 기록)"
    fetched = old.get("fetched_at") or old.get("downloaded_at")
    if not fetched or (old.get("sha256") and not same):
        fetched = datetime.fromtimestamp(m["newest"], timezone.utc).isoformat(timespec="seconds")
    lock[rec["name"]] = {
        "source": rec.get("source") or old.get("source", ""),
        "version": version,
        "license": rec.get("license") or old.get("license", ""),
        "use": old.get("use") or use,
        "files": m["files"],
        "bytes": m["bytes"],
        "sha256": m["sha256"],
        "fetched_at": fetched,
        "measured_at": _now(),
    }
    save(lock)


def wrap(module):
    """module.fetch 를 감싸 끝날 때 update() 를 부른다. 반환값(rec)은 그대로."""
    if getattr(module.fetch, "_manifest", False):
        return
    original = module.fetch
    use = (module.__doc__ or "").strip().splitlines()[0] if module.__doc__ else ""

    @functools.wraps(original)
    def fetch(dest, *args, **kwargs):
        rec = original(dest, *args, **kwargs)
        try:
            update(rec, dest, use)
        except OSError as e:  # 기록 실패가 받기 결과를 망치지 않게
            print(f"[manifest] {rec.get('name')} 기록 실패: {e}")
        return rec

    fetch._manifest = True
    module.fetch = fetch


def refresh():
    """sources/ 의 폴더를 다시 잰다 (version·license 는 이전 기록 유지)."""
    lock = load()
    for d in sorted(p for p in SOURCES_DIR.iterdir() if p.is_dir()):
        update({"name": d.name, **lock.get(d.name, {})}, d)
    return load()


def print_table(lock):
    print(f"{'NAME':28} {'파일':>5} {'MB':>8}  {'버전':24} 라이선스")
    total = 0
    for name, r in lock.items():
        v = r["version"].replace("commit ", "").replace("revision ", "")
        print(f"{name:28} {r['files']:>5} {r['bytes'] / 1e6:>8.1f}  {v[:24]:24} {r['license'][:40]}")
        total += r["bytes"]
    print(f"{'합계 (' + str(len(lock)) + '개)':28} {sum(r['files'] for r in lock.values()):>5} {total / 1e6:>8.1f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print_table(refresh())
    print(f"\n기록 파일: {LOCK}")
