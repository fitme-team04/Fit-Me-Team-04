#!/usr/bin/env bash
# 목적: db/예시_코드 의 예시를 폴더 단위로 차례로 실행 → 파일마다 종료 코드, 끝에 성공·실패 요약
# 사용: bash db/예시_코드/예시_실행.sh                         (그룹/단계 폴더별 파일 수 목록 + 사용법)
#       bash db/예시_코드/예시_실행.sh <그룹>/<단계>            (단계 하나: 01 → 10)
#       bash db/예시_코드/예시_실행.sh <그룹>                   (그룹 하나: 단계 이름 순)
#       bash db/예시_코드/예시_실행.sh all --quiet             (전부, 예시 출력은 숨기고 파일별 상태 줄만)
#       bash db/예시_코드/예시_실행.sh --first                 (찾은 첫 파일 하나만, 대상을 주면 그 안의 첫 파일)
# 그룹·단계는 폴더에서 찾음 (규칙은 _목록.sh): 폴더를 더하면 코드 수정 없이 목록·실행에 들어감
# 파이썬: 환경 변수 PYTHON → 저장소 루트 .venv/bin/python → python3 순서
# 예시는 저장소 루트에서 실행 (예시의 --save 출력 out/ 도 루트 기준). 하나가 실패해도 끝까지 돌고, 실패가 있으면 종료 코드 1
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)   # 예시_코드
ROOT=$(cd "$HERE/../.." && pwd)                        # 예시_코드 → db → 저장소 루트
SELF="bash db/예시_코드/예시_실행.sh"
. "$HERE/_목록.sh"
ex_scan "$HERE"

# 파이썬 고르기 (PYTHON 이 상대 경로면 부른 위치 기준으로 바꿔 둠: 실행은 루트에서 하므로)
PY=${PYTHON:-}
if [ -z "$PY" ]; then
  if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; else PY=python3; fi
elif [ "${PY#/}" = "$PY" ] && [ "${PY#*/}" != "$PY" ]; then
  PY="$PWD/$PY"
fi

usage() {
  local levels
  levels=$(ex_level_names | tr '\n' ' ')
  echo "사용: $SELF [all | <그룹> | <그룹>/<단계>] [--quiet] [--first]"
  echo "  그룹 = ${EX_GROUPS[*]:-(없음)}"
  echo "  단계 = ${levels:-(없음)}  (인자 없으면 폴더 목록)"
}

# 인자 없음: 그룹/단계 폴더마다 파일 수
list_dirs() {
  local d n total=0
  echo "예시 폴더 (파일 수) — 파이썬: $PY"
  for d in "${EX_LEVEL_DIRS[@]}"; do
    n=$(ex_files_in "$HERE/$d" | wc -l)
    total=$((total + n))
    printf '  %s  %d\n' "$d" "$n"
  done
  echo "합계 $total"
  usage
}

# 값이 배열 원소 중 하나면 0 ($1 = 값, 나머지 = 원소)
is_one_of() {
  local x=$1 y
  shift
  for y in "$@"; do [ "$x" = "$y" ] && return 0; done
  return 1
}

# --- 인자 읽기 ---------------------------------------------------------------
quiet=0
first=0
target=""
for a in "$@"; do
  case "$a" in
    --quiet|-q) quiet=1 ;;
    --first) first=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "모르는 옵션: $a"; usage; exit 2 ;;
    *)
      if [ -n "$target" ]; then echo "대상은 하나만: $target / $a"; usage; exit 2; fi
      target=$a ;;
  esac
done

if [ "${#EX_LEVEL_DIRS[@]}" -eq 0 ]; then
  echo "예시 폴더를 찾지 못함: $HERE 아래 <그룹>/<단계>/NN_….py"
  exit 2
fi

if [ -z "$target" ]; then
  if [ "$first" = 0 ]; then
    list_dirs
    exit 0
  fi
  target=all
fi

# 대상 → 실행할 폴더 목록 (db/예시_코드/ 로 시작하거나 끝에 / 가 있어도 됨)
target=${target#./}
target=${target#db/예시_코드/}
target=${target%/}
dirs=()
if [ "$target" = all ]; then
  for d in "${EX_LEVEL_DIRS[@]}"; do dirs+=("$HERE/$d"); done
elif is_one_of "$target" "${EX_GROUPS[@]}"; then
  while IFS= read -r d; do dirs+=("$HERE/$d"); done < <(ex_levels_of "$target")
elif [ -d "$HERE/$target" ] && ex_has_files "$HERE/$target"; then
  dirs=("$HERE/$target")
else
  echo "그룹·단계 폴더가 아님: $target"
  usage
  exit 2
fi

# --- 파일마다 실행 (set -e 없음: 실패해도 다음 파일로) -------------------------
ok=0
fail=0
failed=()
done_first=0
for d in "${dirs[@]}"; do
  [ "$done_first" = 1 ] && break
  while IFS= read -r f; do
    rel=${f#"$ROOT"/}
    echo "■ $rel"
    if [ "$quiet" = 1 ]; then
      out=$(cd "$ROOT" && "$PY" "$rel" </dev/null 2>&1)
      code=$?
    else
      (cd "$ROOT" && "$PY" "$rel" </dev/null)
      code=$?
    fi
    if [ "$code" -eq 0 ]; then
      ok=$((ok + 1))
      echo "  → 성공"
    else
      fail=$((fail + 1))
      failed+=("$rel (종료 코드 $code)")
      echo "  → 실패 (종료 코드 $code)"
      if [ "$quiet" = 1 ] && [ -n "$out" ]; then
        echo "     마지막 줄: $(printf '%s\n' "$out" | tail -n 1)"
      fi
    fi
    if [ "$first" = 1 ]; then
      done_first=1
      break
    fi
  done < <(ex_files_in "$d")
done

echo
echo "성공 $ok / 실패 $fail"
if [ "$fail" -gt 0 ]; then
  echo "실패 목록:"
  for x in "${failed[@]}"; do echo "  $x"; done
  exit 1
fi
exit 0
