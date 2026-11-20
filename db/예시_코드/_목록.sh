# 목적: 예시 그룹·단계·파일을 폴더에서 찾기 — 예시_실행.sh 와 예시_목록_갱신.sh 가 source (이름을 코드에 적지 않음)
# 규칙: db/예시_코드 아래 폴더(_*·__pycache__·out 제외)에서 [0-9][0-9]_*.py 가 있는 폴더 = 단계, 그 부모 폴더 = 그룹
#       순서: 공통/ 아래 그룹 먼저, 나머지 그룹은 이름 순 / 단계·파일도 이름 순 (모두 LC_ALL=C 바이트 순)
# 쓰는 법: . _목록.sh; ex_scan <예시_코드 폴더>
#       → EX_GROUPS (그룹 상대 경로), EX_LEVEL_DIRS (<그룹>/<단계> 상대 경로), ex_files_in <폴더> (파일 전체 경로, 이름 순)

# 폴더 안에 예시 파일(NN_….py)이 하나라도 있으면 0
ex_has_files() {
  local f
  for f in "$1"/[0-9][0-9]_*.py; do
    [ -f "$f" ] && return 0
  done
  return 1
}

# 폴더 안 예시 파일 전체 경로, 이름 순
ex_files_in() {
  local f
  for f in "$1"/[0-9][0-9]_*.py; do
    [ -f "$f" ] && printf '%s\n' "$f"
  done | LC_ALL=C sort
}

# 폴더를 차례로 내려가며 "<그룹>\t<단계>" 출력 ($1 = 맨 위, $2 = 맨 위 기준 상대 경로, 처음엔 빈 값)
_ex_walk() {
  local top=$1 rel=$2 d name
  for d in "$top${rel:+/$rel}"/*/; do
    [ -d "$d" ] || continue
    d=${d%/}
    name=${d##*/}
    case "$name" in _*|__pycache__|out) continue ;; esac
    if [ -n "$rel" ] && ex_has_files "$d"; then
      printf '%s\t%s\n' "$rel" "$name"
    fi
    _ex_walk "$top" "${rel:+$rel/}$name"
  done
}

# EX_GROUPS·EX_LEVEL_DIRS 채우기
ex_scan() {
  local top=$1 tab=$'\t' flag g l last=""
  EX_GROUPS=()
  EX_LEVEL_DIRS=()
  while IFS="$tab" read -r flag g l; do
    [ -n "$g" ] || continue
    if [ "$g" != "$last" ]; then
      EX_GROUPS+=("$g")
      last=$g
    fi
    EX_LEVEL_DIRS+=("$g/$l")
  done < <(
    _ex_walk "$top" "" | while IFS="$tab" read -r g l; do
      case "$g" in 공통/*) flag=0 ;; *) flag=1 ;; esac
      printf '%s\t%s\t%s\n' "$flag" "$g" "$l"
    done | LC_ALL=C sort -t "$tab" -k1,1 -k2,2 -k3,3
  )
}

# 그룹 하나의 단계 폴더 (<그룹>/<단계>), 순서대로
ex_levels_of() {
  local d
  for d in "${EX_LEVEL_DIRS[@]}"; do
    [ "${d%/*}" = "$1" ] && printf '%s\n' "$d"
  done
}

# 단계 이름 목록 (중복 없이, 처음 나온 순서)
ex_level_names() {
  local d n seen=" "
  for d in "${EX_LEVEL_DIRS[@]}"; do
    n=${d##*/}
    case "$seen" in *" $n "*) continue ;; esac
    seen="$seen$n "
    printf '%s\n' "$n"
  done
}
