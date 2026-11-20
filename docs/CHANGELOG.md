# CHANGELOG

## 버전 규칙
- 코드: PoC 동안 `v0.MINOR.PATCH`.
  - MINOR: 새 기능·새 폴더 (예: 적재 코드 추가 → v0.2.0)
  - PATCH: 고침 (예: SQL 오타 수정 → v0.1.1)
- DB 스키마: `db/sql/` 의 가장 큰 `NN_` 파일 번호가 스키마 버전이다.
  - 컬럼을 바꿀 때는 이미 적용한 파일을 고치지 않고, 새 번호 파일(`ALTER TABLE ...`)을 추가한다.
- 데이터: `opensource/sources/sources.lock.json` 과 각 fetch 모듈에 적힌 commit/revision 이 데이터 버전이다. (`sources/` 자체는 커밋하지 않음)
- 파이썬 패키지: `requirements.txt` 에 버전을 고정한다. 바꾸면 여기에 적는다.

## Git 사용법
- 순서: `git pull` → 수정 → `git commit` → 이 파일에 한 줄 추가.
- 커밋 메시지는 `[폴더] 무엇을` 형식. 예: `[db] 컬럼 추가`, `[fetch] nhanes 경로 수정`.
- `opensource/sources/`(받은 데이터)와 `.env`(API 키·비밀번호)는 `.gitignore` 로 빠져 있다. 키·비밀번호는 절대 커밋하지 않는다.

## v0.2.0 — 2026-11-05
명명 규칙 적용 (SQL Style Guide, https://www.sqlstyle.guide/). **호환 안 되는 이름 변경**: v0.1.0 테이블·컬럼·뷰·값을 쓰는 코드와 DB 는 다시 만들어야 한다.
- 테이블: 복수형, 스키마 이름 반복 제거 (예: `body.body_profile` → `body.profiles`, `ref.measure_def` → `ref.measure_definitions`). 뷰 `v_` 접두어 제거 (`body.measure_details`, `arm_measures` …)
- 컬럼: `id` → `<대상>_id`, 예약어·모호한 이름 변경 (`name` → `user_name` 등, `type` → `measure_type`, `source` → `source_name`), 두 FK 역할 이름 (`body_measure_code`, `garment_measure_code`)
- 우리 값은 밑줄: `uniqlo-site` → `uniqlo_site` 등. fetch `NAME`·`sources/` 폴더·`sources.lock.json` 키도 같이 바꿈 (다시 받지 않고 이동, 해시 같음)
- CHECK 제약 추가 (body·garment): 허용값·형식. 규칙과 허용값은 `db/테이블_정의서/공통.xlsx` 명명 규칙·표준 용어 시트
- 테이블 정의서·예시 데이터를 스키마별로 나눔: `db/테이블_정의서/`(ref·body·garment.xlsx + 공통.xlsx 스키마 요약·메모·명명 규칙·표준 용어), `db/예시_데이터/`(ref·body·garment.xlsx). 예전 한 파일은 `.temp` 로 옮김
- 실행 스크립트 하나: `setup.sh` 가 로컬 PC(WSL Rocky 8)·Linux VM 공통, 환경 차이는 `.env` 값만 — `.env` 읽기(없으면 `.env.example` 복사) → `APP_DIR`(기본 `$HOME/poc-size-ai`, 저장소 경로면 복사 없이 그 자리)로 복사 → `/etc/os-release` 배포판 감지(rocky·almalinux·rhel·ol / centos / fedora / ubuntu / debian / amzn 2023·2) → Docker 공식 방법 설치·시작(systemd 없으면 dockerd) → `db/up.sh` → 예시 데이터·행 수 → venv 되는 python 3.9+ 없을 때만 배포판별 패키지 → `.venv` + PyMySQL·`공통/브랜드/1_기본/브랜드_목록.py`. 앞단만 다름: 로컬은 `windows_setup.cmd`, VM 은 `git clone`/`git pull`. `db/up.sh` 가 `.env` 값(컨테이너·볼륨·이미지·포트·비밀번호)을 읽음
- `실행_가이드.txt` (따라 하기용 평문): 준비(A 로컬 더블클릭 / B VM clone·`bash setup.sh`) → 사용(`cd ~/poc-size-ai`·`.venv/bin/python` 예시) → 다시 반영·켜기 + 막힐 때. 작업 중 따로 있던 VM 전용 스크립트·로컬/VM 안내 두 개는 이 둘로 합치고 `.temp` 로 옮김
- `windows_setup.cmd` 추가 (더블클릭 → 관리자 권한 자동 요청, 다시 실행해도 안전, 고정 경로 없음): 관리자·Windows 빌드 19041+·BIOS 가상화 확인 → WSL·VirtualMachinePlatform 기능 켜기(켜면 재부팅 안내 후 종료) → `wsl --update` → Rocky 8 없으면 받아서 가져오기 → `.env` 없으면 복사 → Rocky8 `/etc/wsl.conf` systemd 켜고 Rocky8 만 `wsl --terminate` → `wsl --cd <이 폴더> -- bash setup.sh`(종료 코드 전달). `setup.sh` 는 Windows PATH(`/mnt/...`) 제외(Docker Desktop docker 방지)·예시 데이터 적재·행 수·`$APP_DIR/.venv` + `requirements.txt` 의 PyMySQL 만 설치·예시 하나(`공통/브랜드/1_기본/브랜드_목록.py`) 실행까지, `db/up.sh` 컨테이너 `--restart unless-stopped`, `.gitignore` 에 `.venv/`, `.gitattributes` 에 `*.cmd` CRLF
- `db/예시_코드/` 추가: 파이썬 예시(`_db.py` 접속 도우미 + 아래 파트별 파일), `requirements.txt` 에 `PyMySQL==1.2.3` 고정
- `db/예시_코드/` 파트별 폴더 + 목적을 적은 한글 파일 이름으로 정리 (16개, 파일·함수마다 `# 목적:` 주석): `3d/`(치수항목_부위별_목록·부위별_신체치수_JSON·옷_사이즈별_치수_JSON·옷_특정치수_찾기·조건별_사람_찾기) · `ai/`(학습용_데이터표_만들기·회귀_키로_치수_예측·분류_사이즈_예측·최근접이웃_치수_추정·규칙_사이즈_추천·출처별_치수이름_변환표) · `front/`(입력값_검증·사용자_신체정보_저장·추천_요청_처리·사용자_목록_조회·브랜드_옷_목록_조회). 처음 만든 스키마별 조회 3개는 기능별로 나눠 넣고 원본은 `.temp` 로. `_db.py` 에 쓰기·`save_text` 도우미, `--save` 출력은 `out/`(`.gitignore`), `setup.sh` 시험 실행은 `공통/브랜드/1_기본/브랜드_목록.py`, `실행_가이드.txt` 2번을 2-1 3D · 2-2 AI · 2-3 프론트로
- `db/예시_코드/` 난이도(SQL 복잡도)별 폴더 `1_기본`·`2_심화`·`3_고급` + `공통/`(브랜드·사람·옷 9개 새 예시, 예: 유니클로 옷 목록·브랜드 사이즈표·`LAG` 사이즈 비교)로 나눔, 3d·ai·front 빈 단계 새 예시 4개, 공통과 겹친 조회(사용자·브랜드 목록)는 공통으로 합침, 서로 import 하던 함수는 `_추천.py`·`_추정.py`·`_검증.py`·`_학습표.py` 로 빼고 쪼갠 원본은 `.temp`, `setup.sh` 시험 실행·`실행_가이드.txt` 3번(3-1 공통 ~ 3-4 프론트)·README 표 갱신
- `db/예시_코드/` 예시 180개로 확장: 그룹 6개(`공통/브랜드`·`공통/사람`·`공통/옷`·`3d`·`ai`·`front`) × `1_기본`·`2_심화`·`3_고급` × 10개, 단계 안은 SQL 복잡도 순 `01_`~`10_` 번호(기존 파일도 번호 붙여 이름 변경). 실행기 `db/예시_코드/예시_실행.sh` 추가(폴더 목록 / 단계·그룹·`all`, `--quiet`, 끝에 `성공 N / 실패 M`, 실패 있으면 종료 코드 1). `setup.sh` 시험 실행을 `01_브랜드_목록.py` 로, `실행_가이드.txt` 3번을 3-1 공통/브랜드 ~ 3-6 프론트 실행기 명령으로, README 짧게, 도우미 `누가 쓰나`·문서의 옛 경로 갱신
- 최상위 폴더 이름 영어로: `아키텍처/` → `architecture/`, `오픈소스/` → `opensource/` (`.gitignore`·`setup.sh` 복사 제외·README 링크·`산출물_관리대장.xlsx` 경로 같이 바꿈)
- `db/up.sh` 포트를 `DB_BIND`(기본 `127.0.0.1`)에만 엶 (`-p ${DB_BIND}:${DB_PORT}:3306`, `.env.example` 에 `DB_BIND` 추가). 이미 있는 컨테이너는 그대로. `db/예시_코드/README.md` 접속 설명을 "Docker 와 같은 OS 안에서 실행"으로 고침
- 배포 전이라 `db/sql/` CREATE 파일을 ALTER 파일 없이 그 자리에서 고침 (위 버전 규칙의 예외). SQL 파일 이름도 새 테이블 이름으로 바꿈
- fetch catalog 그룹(사이즈 없는 5개 소스) 제외 → 그룹 4개·소스 14개, .temp 보관

## v0.1.0 — 2026-11-05
처음 기록. 지금 있는 것:
- `오픈소스/fetch/` 수집 패키지: 그룹 5개(body·catalog·fit·garment·model), 모듈 19개
- `오픈소스/fetch/manifest.py`: 받은 데이터 목록 자동 기록 (`sources/sources.lock.json`)
- `오픈소스/오픈소스_조사.xlsx`
- `db/`: `up.sh`(MySQL 8.0 Docker), `sql/` 17개(00_ ~ 53_, 스키마 버전 53), `query/` 15개, `테이블_정의서.xlsx`
- `아키텍처/`: ERD, 데이터흐름, Azure구성 (.drawio + .png)
- `산출물_관리대장.xlsx`
- README (루트, 아키텍처, db, db/query, 오픈소스, fetch 각 그룹)
- `requirements.txt` (버전 고정)

아직 없음: 적재 코드, AI 추정 모델, 3D
