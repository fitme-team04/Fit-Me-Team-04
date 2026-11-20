# db — PoC 데이터베이스 (MySQL 8.0, Docker)

Azure SQL에 배포하는 3D 서비스는 [azure/3d/](azure/3d/README.md)를 참고합니다. 상품·실측·치수 정의는 기존 구조를 재사용하며 MySQL용 초기화 SQL과 Azure T-SQL을 구분합니다.

## 들어 있는 것
| 파일·폴더 | 하는 일 |
|---|---|
| `up.sh` | MySQL 컨테이너 `poc-mysql` 를 만들거나 시작하고 `sql/*.sql` 을 순서대로 적용 |
| `sql/` | 초기화 세트: 스키마 `body`(사람 치수) / `garment`(옷 치수) / `ref`(치수 항목 정의) + 시드 |
| `query/` | 목적별 사용 SQL (회원·신체·옷·추천·학습·점검) — 필요한 폴더만 열면 됨 |
| [예시_코드/](<예시_코드/README.md>) | 공통(브랜드·사람·옷)·파트(3D·AI·프론트)별, 난이도(1_기본·2_심화·3_고급)별 `01_`~`10_` 번호 붙은 목적 이름 파이썬 예시 180개 (PyMySQL, 컨테이너 실행 전제) — `python db/예시_코드/공통/브랜드/2_심화/01_브랜드별_옷_목록.py`, 폴더째 실행은 `bash db/예시_코드/예시_실행.sh 공통/브랜드/2_심화` |
| [테이블_정의서/](<테이블_정의서/>) | 스키마별 `ref`·`body`·`garment.xlsx`: 테이블 목록(예상 건수·용량)·컬럼 정의·인덱스 / `공통.xlsx`: 스키마 요약·메모·명명 규칙·표준 용어 (`sql/` 과 같음) |
| [예시_데이터/](<예시_데이터/>) · [sample/sample_data.sql](sample/sample_data.sql) | 스키마별 `ref`·`body`·`garment.xlsx` 에 테이블별 예시 행(최대 20개, 실데이터 출처) — SQL 은 `up.sh` 가 아니라 루트 `setup.sh` 가 적재 (여러 번 해도 같은 결과) |
| [ERD](../architecture/ERD.png) | 테이블 관계도 (`3. 코딩/architecture/ERD.png`) |

## 사용법
1. Docker Desktop 을 켠다.
2. `bash up.sh` 실행 (Windows Git Bash 는 `MSYS_NO_PATHCONV=1 bash up.sh`). 여러 번 실행해도 안전.
3. 접속: `docker exec -it poc-mysql mysql -uroot -ppoc-root` 또는 `mysql -h 127.0.0.1 -P 3306 -uroot -p`
4. 끄기: `docker stop poc-mysql` (데이터는 볼륨 `poc-mysql-data` 에 남음)
5. 다음: 테이블을 바꾸려면 `sql/`, 데이터를 쓰거나 볼 때는 `query/`
6. 로컬 PC(WSL Rocky 8)·Linux VM 에서 띄우기: 같은 루트 `setup.sh` (로컬은 `windows_setup.cmd` 더블클릭이 실행, VM 은 `bash setup.sh`) — 예시 데이터·파이썬 예시까지 자동, 컨테이너는 `--restart unless-stopped` (`../실행_가이드.txt`(공개 레포에는 없음))

## 주의
- 기본값: 여는 주소 `DB_BIND=127.0.0.1`(이 컴퓨터 안에서만), 포트 `DB_PORT=3306`, 비밀번호 `MYSQL_ROOT_PASSWORD=poc-root` (예: `DB_PORT=3307 bash up.sh`). 비밀번호·주소·포트는 컨테이너를 처음 만들 때만 적용.
- 컨테이너·볼륨 삭제(`docker rm`, `docker volume rm`)는 데이터가 사라지므로 하지 않는다.
