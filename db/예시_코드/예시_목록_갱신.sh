#!/usr/bin/env bash
# 목적: db/예시_코드 폴더를 읽어 실행_가이드.txt (3. 사용) · 명령어_모음.txt (파이썬 절) 의 예시 목록을 다시 씀
# 사용: bash db/예시_코드/예시_목록_갱신.sh [저장소 루트]      (setup.sh 가 복사 전에 실행, 기본 루트 = 이 파일의 ../..)
# 그룹·단계·파일 찾기 규칙은 _목록.sh (예시_실행.sh 와 같음). 파일마다 첫 '# 목적:' 줄, '# 난이도:' 첫 낱말과 — 뒤 글, 첫 '# 출력:' 줄을 읽음
# 명령어_모음 쪽은 파일마다 'NN 목적' / '  왜 이렇게 : (난이도 — 뒤)' / '  출력      : (# 출력:, 없으면 줄 생략)' / 명령
# 두 표시 줄 사이만 바꿈, 밖은 한 바이트도 안 바꿈. 표시 줄이 없으면 한 번만 제자리에 넣음
# 줄바꿈(CRLF/LF)·UTF-8 은 원래 파일 그대로, 같은 폴더 임시 파일에 쓴 뒤 mv. 시각 없음 → 두 번 돌려도 같은 바이트
# python 필요 없음 (bash·sort·mktemp·cmp·mv 만)
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=${1:-$(cd "$HERE/../.." && pwd)}
EX_DIR="$ROOT/db/예시_코드"
START='#### 자동 생성 시작 — 예시 목록 (setup.sh 가 만듦, 직접 고치지 말 것)'
END='#### 자동 생성 끝'
RUN="bash db/예시_코드/예시_실행.sh"

. "$HERE/_목록.sh"
[ -d "$EX_DIR" ] || { echo "    [경고] 예시 폴더 없음: $EX_DIR" >&2; exit 1; }
ex_scan "$EX_DIR"
if [ "${#EX_LEVEL_DIRS[@]}" -eq 0 ]; then
  echo "    [경고] 예시 파일을 찾지 못함 ($EX_DIR/<그룹>/<단계>/NN_….py) — 목록을 바꾸지 않음" >&2
  exit 1
fi

# 명령 줄에 넣을 경로: 빈칸이 있으면 큰따옴표
q() {
  case "$1" in *' '*) printf '"%s"' "$1" ;; *) printf '%s' "$1" ;; esac
}

# 예시 파일 머리 읽기 → H_PURPOSE (첫 '# 목적:' 뒤 글), H_LEVEL ('# 난이도:' 첫 낱말),
#   H_REASON ('# 난이도:' 줄의 첫 — 뒤 글, — 가 없으면 빈칸), H_OUT (첫 '# 출력:' 뒤 글, 없으면 빈칸)
read_head() {
  local line p="" w="" r="" o="" lv=0
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line%$'\r'}
    if [ -z "$p" ] && [[ $line == "# 목적:"* ]]; then
      p=${line#"# 목적:"}
      p=${p#"${p%%[![:space:]]*}"}
    fi
    if [ "$lv" = 0 ] && [[ $line == "# 난이도:"* ]]; then
      lv=1
      w=${line#"# 난이도:"}
      w=${w#"${w%%[![:space:]]*}"}
      if [[ $w == *"—"* ]]; then
        r=${w#*"—"}
        r=${r#"${r%%[![:space:]]*}"}
        r=${r%"${r##*[![:space:]]}"}
      fi
      w=${w%%[[:space:]]*}
    fi
    if [ -z "$o" ] && [[ $line == "# 출력:"* ]]; then
      o=${line#"# 출력:"}
      o=${o#"${o%%[![:space:]]*}"}
    fi
    [ -n "$p" ] && [ "$lv" = 1 ] && [ -n "$o" ] && break
  done < "$1"
  H_PURPOSE=$p
  H_LEVEL=$w
  H_REASON=$r
  H_OUT=$o
}

# --- 목록 만들기 ---------------------------------------------------------------
GUIDE=()   # 실행_가이드.txt 표시 줄 사이
CMDS=()    # 명령어_모음.txt 표시 줄 사이
total=0
gi=0
for g in "${EX_GROUPS[@]}"; do
  gi=$((gi + 1))
  gtotal=0
  counts=()
  tags=()
  levels=()
  body=()
  while IFS= read -r ld; do
    levels+=("$ld")
    files=()
    while IFS= read -r f; do files+=("$f"); done < <(ex_files_in "$EX_DIR/$ld")
    n=${#files[@]}
    tag=""
    body+=("")
    hi=${#body[@]}
    body+=("")                       # 단계 머리 줄 자리 (난이도를 읽은 뒤 채움)
    body+=("[Rocky8 / VM 터미널]")
    for f in "${files[@]}"; do
      read_head "$f"
      [ -n "$tag" ] || tag=$H_LEVEL
      base=${f##*/}
      purpose=$H_PURPOSE
      if [ -z "$purpose" ]; then purpose=${base%.py}; purpose=${purpose#??_}; purpose=${purpose//_/ }; fi
      body+=("${base:0:2} $purpose")
      [ -n "$H_REASON" ] && body+=("  왜 이렇게 : $H_REASON")
      [ -n "$H_OUT" ] && body+=("  출력      : $H_OUT")
      body+=("    .venv/bin/python $(q "db/예시_코드/${f#"$EX_DIR"/}")")
    done
    if [ -z "$tag" ]; then tag=${ld##*/}; tag=${tag#*_}; fi   # '# 난이도:' 가 없으면 폴더 이름 1_기본 → 기본
    body[hi]="$ld [$tag] (${n}개)"
    tags+=("$tag")
    counts+=("$n")
    gtotal=$((gtotal + n))
  done < <(ex_levels_of "$g")
  total=$((total + gtotal))

  # 실행_가이드: 3-N 그룹 (파일 수) → 단계마다 태그 줄 + 명령 → OK 줄
  [ "$gi" -gt 1 ] && GUIDE+=("")
  GUIDE+=("3-$gi $g (${gtotal}개)")
  for i in "${!levels[@]}"; do
    GUIDE+=("[Rocky8 / VM 터미널] [${tags[i]}]")
    GUIDE+=("    $RUN $(q "${levels[i]}")")
  done
  same=1
  for c in "${counts[@]}"; do [ "$c" = "${counts[0]}" ] || same=0; done
  if [ "$same" = 1 ]; then
    GUIDE+=("→ 단계마다 성공 ${counts[0]} / 실패 0 이면 OK")
  else
    joined=$(IFS='·'; echo "${counts[*]}")
    GUIDE+=("→ 단계 순서대로 성공 $joined / 실패 0 이면 OK")
  fi

  # 명령어_모음: 단계마다 머리 줄 + 파일마다 제목 줄·명령
  CMDS+=("${body[@]}")
done
CMDS=("→ 그룹 ${#EX_GROUPS[@]}개 · 단계 ${#EX_LEVEL_DIRS[@]}개 · 파일 ${total}개, 0-1·0-2 로 들어가 cd ~/poc-size-ai 뒤 한 줄씩" "${CMDS[@]}")

# --- 파일 다시 쓰기 ---------------------------------------------------------------
# rewrite <파일> <guide|cmds> <배열 이름>
rewrite() {
  local file=$1 mode=$2 arr=$3 line last_nl=1 cr="" i s=-1 e=-1 ns=0 ne=0 a b x tmp state
  local -a L=() OUT=() PRE=() GEN=()
  eval 'GEN=("${'"$arr"'[@]}")'
  if [ ! -f "$file" ]; then
    echo "    [경고] ${file##*/} 없음 — 건너뜀" >&2
    return 0
  fi
  while IFS= read -r line; do L+=("$line"); done < "$file"
  if [ -n "$line" ]; then L+=("$line"); last_nl=0; fi
  [ "${#L[@]}" -gt 0 ] && [ "${L[0]%$'\r'}" != "${L[0]}" ] && cr=$'\r'

  for i in "${!L[@]}"; do
    x=${L[i]%$'\r'}
    if [ "$x" = "$START" ]; then s=$i; ns=$((ns + 1)); fi
    if [ "$x" = "$END" ]; then e=$i; ne=$((ne + 1)); fi
  done

  if [ "$ns" = 1 ] && [ "$ne" = 1 ] && [ "$e" -gt "$s" ]; then
    a=$((s + 1)); b=$e                       # 표시 줄은 그대로 두고 사이만
  elif [ "$ns" = 0 ] && [ "$ne" = 0 ]; then
    if ! find_place "$mode"; then
      echo "    [경고] ${file##*/}: 넣을 자리를 못 찾음 — 건너뜀" >&2
      return 0
    fi
    a=$P_A; b=$P_B
    PRE=("${P_PRE[@]}" "$START")
    GEN+=("$END")
  else
    echo "    [경고] ${file##*/}: 표시 줄이 짝이 안 맞음 (시작 $ns · 끝 $ne) — 건너뜀" >&2
    return 0
  fi

  OUT=("${L[@]:0:a}")
  for x in "${PRE[@]}" "${GEN[@]}"; do OUT+=("$x$cr"); done
  OUT+=("${L[@]:b}")

  tmp=$(mktemp "${file%/*}/.예시목록.XXXXXX") || { echo "    [경고] 임시 파일을 못 만듦 — ${file##*/} 건너뜀" >&2; return 0; }
  {
    for i in "${!OUT[@]}"; do
      if [ "$last_nl" = 0 ] && [ "$i" -eq $((${#OUT[@]} - 1)) ]; then
        printf '%s' "${OUT[i]}"
      else
        printf '%s\n' "${OUT[i]}"
      fi
    done
  } > "$tmp"
  chmod --reference="$file" "$tmp" 2>/dev/null || true
  if cmp -s "$tmp" "$file"; then state=그대로; else state=바뀜; fi
  mv -f "$tmp" "$file"
  printf '%s' "${file##*/} $state"
}

# 표시 줄이 없을 때 넣을 자리 → P_A..P_B 를 바꿈 (P_B 앞까지), 앞에 P_PRE 줄
#   guide: '3. ' 절 안 '3-N ' 줄부터 다음 'N. ' 절 앞 마지막 글 줄까지 (3-N 이 없으면 그 절 끝에 빈 줄 하나 두고)
#   cmds : '==== N. 파이썬' 절 끝 (다음 '==== ' 앞 마지막 글 줄 뒤) 에 빈 줄 + 'N-(마지막+1) 예시 전체 목록'
find_place() {
  local mode=$1 i x h=-1 nh first=-1 lastnb=-1 num max=0 re
  P_PRE=()
  if [ "$mode" = guide ]; then
    for i in "${!L[@]}"; do [[ ${L[i]%$'\r'} == "3. "* ]] && { h=$i; break; }; done
    [ "$h" -ge 0 ] || return 1
    nh=${#L[@]}
    re='^[0-9]+\. '
    for ((i = h + 1; i < ${#L[@]}; i++)); do [[ ${L[i]%$'\r'} =~ $re ]] && { nh=$i; break; }; done
    re='^3-[0-9]+ '
    for ((i = h + 1; i < nh; i++)); do
      x=${L[i]%$'\r'}
      [ "$first" -lt 0 ] && [[ $x =~ $re ]] && first=$i
      [[ $x == *[![:space:]]* ]] && lastnb=$i
    done
    if [ "$first" -ge 0 ]; then
      P_A=$first; P_B=$((lastnb + 1))
    else
      P_A=$((lastnb + 1)); P_B=$P_A; P_PRE=("")
    fi
  else
    re='^==== ([0-9]+)\. 파이썬'
    for i in "${!L[@]}"; do [[ ${L[i]%$'\r'} =~ $re ]] && { h=$i; num=${BASH_REMATCH[1]}; break; }; done
    [ "$h" -ge 0 ] || return 1
    nh=${#L[@]}
    for ((i = h + 1; i < ${#L[@]}; i++)); do [[ ${L[i]%$'\r'} == "==== "* ]] && { nh=$i; break; }; done
    re="^$num-([0-9]+) "
    for ((i = h + 1; i < nh; i++)); do
      x=${L[i]%$'\r'}
      [[ $x =~ $re ]] && [ "${BASH_REMATCH[1]}" -gt "$max" ] && max=${BASH_REMATCH[1]}
      [[ $x == *[![:space:]]* ]] && lastnb=$i
    done
    [ "$lastnb" -ge 0 ] || lastnb=$h
    P_A=$((lastnb + 1)); P_B=$P_A
    P_PRE=("" "$num-$((max + 1)) 예시 전체 목록 (파일 하나씩 실행, 폴더 단위는 $num-1)")
  fi
  return 0
}

r1=$(rewrite "$ROOT/실행_가이드.txt" guide GUIDE)
r2=$(rewrite "$ROOT/명령어_모음.txt" cmds CMDS)
echo "    예시 목록: 그룹 ${#EX_GROUPS[@]} · 단계 ${#EX_LEVEL_DIRS[@]} · 파일 ${total}개 → ${r1:-실행_가이드.txt 건너뜀}, ${r2:-명령어_모음.txt 건너뜀}"
