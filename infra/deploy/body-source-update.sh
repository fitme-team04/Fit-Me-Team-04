#!/usr/bin/env bash
# 역할: Git 리비전·해시를 검증한 소스 전용 이미지를 신체 VM에 배포하고 실패하면 이미지와 호스트 소스를 복원합니다.
set -Eeuo pipefail

REVISION=${1:?Usage: body-source-update.sh <40-character Git revision>}
[[ "$REVISION" =~ ^[0-9a-f]{40}$ ]] || { echo 'FAIL: invalid Git revision'; exit 2; }
[[ "$EUID" -eq 0 ]] || { echo 'FAIL: run this deployment as root'; exit 2; }
APP_DIR=/opt/fitme-avatar
RELEASE_DIR="$APP_DIR/releases/$REVISION"
LOCAL_IMAGE=fitme-avatar:local
SOURCE_IMAGE="fitme-avatar:source-$REVISION"
ROLLBACK_IMAGE="fitme-avatar:rollback-$REVISION"
BACKUP_DIR=''
SOURCE_CHANGED=0
IMAGE_CHANGED=0
DEPLOY_PID=$BASHPID

# BEGIN RELEASE VALIDATION
python3 - "$APP_DIR" "$RELEASE_DIR" "$REVISION" <<'PY'
import hashlib,json,re,stat,sys
from pathlib import Path,PurePosixPath
app,release=map(Path,sys.argv[1:3]);revision=sys.argv[3]
if app.resolve()!=app or release.resolve()!=release or not release.is_dir():
    raise SystemExit('FAIL: deployment directories must be real directories without symlinks')
if release.parent!=app/'releases' or release.name!=revision:
    raise SystemExit('FAIL: release is outside the named deployment directory')
manifest_path=release/'manifest.json'
if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size>2_000_000:
    raise SystemExit('FAIL: invalid release manifest')
manifest=json.loads(manifest_path.read_text())
files=manifest.get('files')
if manifest.get('revision')!=revision or not isinstance(files,dict) or not files:
    raise SystemExit('FAIL: release revision or manifest is invalid')
required={'Dockerfile.avatar-source','body-source-update.sh','src/api/avatar.py',
          'src/inference/sam_reference.py','src/core/sam_runtime.py','src/core/photo_visibility.py'}
if not required.issubset(files):raise SystemExit('FAIL: incomplete source release')
for name,digest in files.items():
    if not isinstance(name,str) or '\\' in name or not name or name.startswith('/'):
        raise SystemExit('FAIL: invalid release path')
    path=PurePosixPath(name)
    if any(part in ('','..','.') for part in name.split('/')) or str(path)!=name:
        raise SystemExit('FAIL: release path traversal is forbidden')
    if not (name.startswith('src/') or name in {'Dockerfile.avatar-source','body-source-update.sh'}):
        raise SystemExit('FAIL: unexpected release file')
    if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):
        raise SystemExit('FAIL: invalid release file digest')
    target=release/path
    if any(parent.is_symlink() for parent in (target,*target.parents)):
        raise SystemExit('FAIL: release symlinks are forbidden')
    if not target.is_file() or not stat.S_ISREG(target.stat().st_mode):
        raise SystemExit('FAIL: missing or non-regular release file')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
        raise SystemExit('FAIL: release file checksum mismatch: '+name)
actual=set()
for target in release.rglob('*'):
    if target.is_symlink():raise SystemExit('FAIL: release symlinks are forbidden')
    if target.is_file():actual.add(target.relative_to(release).as_posix())
    elif not target.is_dir():raise SystemExit('FAIL: non-regular release entry')
if actual!=set(files)|{'manifest.json'}:
    raise SystemExit('FAIL: unmanifested or missing release files')
print('PASS: source release verified',revision,len(files),'files',flush=True)
PY
# END RELEASE VALIDATION

cd "$APP_DIR"
exec 9>"$APP_DIR/.body-source-update.lock"
flock -n 9 || { echo 'FAIL: another body deployment is running'; exit 2; }
docker compose -f compose.yaml config -q
COMPOSE_IMAGE=$(docker compose -f compose.yaml config --format json | python3 -c \
    'import json,sys; print(json.load(sys.stdin)["services"]["avatar"]["image"])')
[[ "$COMPOSE_IMAGE" == "$LOCAL_IMAGE" ]] || { echo 'FAIL: unexpected avatar Compose image'; exit 2; }
CONTAINER_ID=$(docker compose -f compose.yaml ps -aq avatar)
[[ -n "$CONTAINER_ID" && "$CONTAINER_ID" != *$'\n'* ]] || { echo 'FAIL: expected one existing avatar container'; exit 2; }
OLD_IMAGE_ID=$(docker inspect --format '{{.Image}}' "$CONTAINER_ID")
[[ "$OLD_IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'FAIL: invalid running image ID'; exit 2; }
OLD_REVISION=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$OLD_IMAGE_ID")

wait_for_health() {
    python3 - "$1" <<'PY'
import json,sys,time,urllib.request
revision=sys.argv[1];deadline=time.monotonic()+150
while time.monotonic()<deadline:
    try:
        remaining=deadline-time.monotonic()
        with urllib.request.urlopen('http://10.4.2.4:8001/health',timeout=max(.1,min(3,remaining))) as response:
            value=json.load(response)
            ready=response.status==200 and value.get('status')=='ok' and value.get('service')=='avatar'
            if revision!='rollback':
                ready=ready and value.get('source_revision')==revision and value.get('photo_framing_check')=='sam_projected_full_body_v1'
            if ready:
                print('PASS: body health',json.dumps({k:value.get(k) for k in ('status','service','source_revision','photo_framing_check')}),flush=True)
                break
    except Exception:
        pass
    time.sleep(max(0,min(2,deadline-time.monotonic())))
else:raise SystemExit('FAIL: body health did not become ready within 150 seconds')
PY
}

verify_live_source() {
    local live_container
    live_container=$(docker compose -f compose.yaml ps -q avatar)
    docker exec "$live_container" /opt/api/bin/python -c '
import hashlib,json,os
from pathlib import Path
manifest=json.loads(Path("/opt/fitme-source/manifest.json").read_text())
assert manifest["revision"]==os.environ["FITME_SOURCE_REVISION"]
expected=set()
for name,digest in manifest["files"].items():
    if not name.startswith("src/"):continue
    path=Path("/app")/name
    assert path.is_file() and not path.is_symlink(), name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, name
    if path.suffix==".py":expected.add(path.relative_to("/app/src").as_posix())
assert {p.relative_to("/app/src").as_posix() for p in Path("/app/src").rglob("*.py")}==expected
print("PASS: live container source matches the Git release",manifest["revision"],flush=True)
'
}

if [[ "$OLD_REVISION" == "$REVISION" ]]; then
    wait_for_health "$REVISION"
    verify_live_source
    echo "PASS: body source revision already deployed $REVISION"
    exit 0
fi

protect_tag() {
    local tag=$1 existing=''
    existing=$(docker image inspect --format '{{.Id}}' "$tag" 2>/dev/null || true)
    [[ -z "$existing" || "$existing" == "$OLD_IMAGE_ID" ]] || { echo 'FAIL: protected image tag already points to a different runtime'; return 1; }
    docker image tag "$OLD_IMAGE_ID" "$tag"
}
protect_tag "$ROLLBACK_IMAGE"
# Pin the already present image ID through a protected local name; no pull is performed.
RUNTIME_IMAGE="fitme-avatar:runtime-${OLD_IMAGE_ID:7:16}"
protect_tag "$RUNTIME_IMAGE"
docker build --pull=false --network=none \
    --build-arg "BASE_IMAGE=$RUNTIME_IMAGE" --build-arg "BASE_IMAGE_ID=$OLD_IMAGE_ID" \
    --build-arg "SOURCE_REVISION=$REVISION" \
    -f "$RELEASE_DIR/Dockerfile.avatar-source" -t "$SOURCE_IMAGE" "$RELEASE_DIR"

# Importing the API does not run its lifespan or allocate a second GPU model.
docker run --rm --network=none --entrypoint /opt/api/bin/python "$SOURCE_IMAGE" -c '
import hashlib,json,os
from pathlib import Path
manifest=json.loads(Path("/opt/fitme-source/manifest.json").read_text())
assert manifest["revision"]==os.environ["FITME_SOURCE_REVISION"]
expected={}
for name,digest in manifest["files"].items():
    if not name.startswith("src/"):continue
    path=Path("/app")/name
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest, name
    if path.suffix==".py":
        compile(path.read_text(encoding="utf-8"),str(path),"exec")
        expected[path.relative_to("/app/src").as_posix()]=digest
actual={p.relative_to("/app/src").as_posix() for p in Path("/app/src").rglob("*.py")}
assert actual==set(expected), "Unexpected Python files in source image"
from api.avatar import app,health
value=health()
assert value["source_revision"]==manifest["revision"]
assert value["photo_framing_check"]=="sam_projected_full_body_v1"
print("PASS: source image checksums, Python syntax and offline API import",flush=True)
'
docker run --rm --network=none --entrypoint /opt/conda/bin/python "$SOURCE_IMAGE" -c \
    'import inference.sam_reference, core.photo_visibility; print("PASS: offline SAM source import",flush=True)'
NEW_IMAGE_ID=$(docker image inspect --format '{{.Id}}' "$SOURCE_IMAGE")

rollback() {
    local result=$1
    # A failed command substitution also inherits ERR; only its parent may restore state.
    if [[ "$BASHPID" != "$DEPLOY_PID" ]]; then
        trap - ERR
        exit "$result"
    fi
    trap - ERR INT TERM
    set +e
    echo "FAIL: deployment stopped; restoring previous body source and image (exit $result)"
    if [[ "$SOURCE_CHANGED" -eq 1 ]]; then
        python3 - "$APP_DIR" "$BACKUP_DIR" <<'PY'
import shutil,sys
from pathlib import Path
app,backup=map(Path,sys.argv[1:])
if app.resolve()!=app or backup.resolve()!=backup or not backup.is_relative_to(app/'source-backups'):
    raise SystemExit('FAIL: refusing source rollback outside the deployment directory')
source=app/'src';saved=backup/'src';failed=backup/'failed-src'
if source.is_symlink() or saved.is_symlink() or not saved.is_dir() or failed.exists():
    raise SystemExit('FAIL: unsafe source rollback state')
if source.exists():source.rename(failed)
shutil.copytree(saved,source,symlinks=True)
print('PASS: previous host source restored; failed source retained in backup',flush=True)
PY
        [[ "$?" -eq 0 ]] || echo 'FAIL: host source recovery needs manual inspection of the retained backup'
    fi
    if [[ "$IMAGE_CHANGED" -eq 1 ]]; then
        docker image tag "$OLD_IMAGE_ID" "$LOCAL_IMAGE"
        docker compose -f compose.yaml up -d --no-deps --no-build --pull never --force-recreate avatar
        wait_for_health rollback || echo 'FAIL: rollback image restored but health needs inspection'
    fi
    exit "$result"
}
trap 'rollback "$?"' ERR
trap 'rollback 130' INT
trap 'rollback 143' TERM

BACKUP_DIR="$APP_DIR/source-backups/$REVISION-$(date -u +%Y%m%dT%H%M%SZ)-$$"
python3 - "$APP_DIR" "$BACKUP_DIR" <<'PY'
import shutil,sys
from pathlib import Path
app,backup=map(Path,sys.argv[1:]);source=app/'src'
if app.resolve()!=app or backup.resolve()!=backup or backup.parent!=app/'source-backups' or backup.exists():
    raise SystemExit('FAIL: unsafe source backup destination')
if source.is_symlink() or not source.is_dir() or any(p.is_symlink() for p in source.rglob('*')):
    raise SystemExit('FAIL: host source must contain no symlinks')
backup.mkdir(parents=True,mode=0o700)
shutil.copytree(source,backup/'src',symlinks=True)
print('PASS: host source backup retained',backup,flush=True)
PY
SOURCE_CHANGED=1
python3 - "$APP_DIR" "$RELEASE_DIR" <<'PY'
import hashlib,json,shutil,sys
from pathlib import Path
app,release=map(Path,sys.argv[1:]);manifest=json.loads((release/'manifest.json').read_text());expected=set()
for name,digest in manifest['files'].items():
    if not name.startswith('src/'):continue
    source=release/name;target=app/name
    if any(p.is_symlink() for p in (target,*target.parents)):
        raise SystemExit('FAIL: refusing to overwrite a source symlink')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
        raise SystemExit('FAIL: release changed after verification')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
        raise SystemExit('FAIL: host source checksum mismatch')
    if target.suffix=='.py':expected.add(target.relative_to(app/'src').as_posix())
actual={p.relative_to(app/'src').as_posix() for p in (app/'src').rglob('*.py')}
if actual!=expected:raise SystemExit('FAIL: host Python source inventory differs from the release')
print('PASS: host source now matches the verified Git release',flush=True)
PY
IMAGE_CHANGED=1
docker image tag "$SOURCE_IMAGE" "$LOCAL_IMAGE"
docker compose -f compose.yaml up -d --no-deps --no-build --pull never --force-recreate avatar
LIVE_CONTAINER=$(docker compose -f compose.yaml ps -q avatar)
[[ "$(docker inspect --format '{{.Image}}' "$LIVE_CONTAINER")" == "$NEW_IMAGE_ID" ]]
wait_for_health "$REVISION"
verify_live_source
trap - ERR INT TERM
echo "PASS: deployed body source $REVISION image $NEW_IMAGE_ID"
