# 입어봄 V2 실행 안내

V2는 판매자가 착용샷으로 얻은 의류 측정 결과, ML팀의 측정 JSON, 태그 카탈로그 값 또는 직접 잰 치수를 매물 단위로 공유한다. 구매자가 링크를 열면 그 옷의 모습과 치수, 출처를 확인할 수 있다. ‘시연용 예시’의 치수는 화면을 체험하기 위한 값이다. 실제로 촬영한 매물의 모델과 치수는 연결된 측정 서비스에서 받아온다.

## 로컬에서 시작하기

팀 MySQL과 원본 신체·의류 테이블, Docker, Python 3.12가 필요하다. 팀 환경이 없는 Windows PC는 V1의 Rocky8 설치 안내(개발용 비공개 레포 `feature/front-test` 브랜치)를 따라 팀 환경을 한 번 준비하고 V2를 별도 폴더에 내려받는다. 이미 설치한 PC에서는 바로 진행한다.

1. Windows에서는 V2 폴더의 `windows_app.cmd`를 실행한다. Rocky8/Linux 터미널에서는 이 체크아웃에서 `bash web/run.sh`를 실행한다.
2. [V2 홈](http://localhost:8766/)을 열고 판매자·구매자 경로를 선택한다. [연결 상태](http://localhost:8766/api/health)에서 `version`이 `2`인지 확인한다.
3. 전용 Redis가 필요하면 스크립트가 `fitme-v2-redis` 컨테이너를 `127.0.0.1:6380`에 시작한다. 첫 실행 시 MySQL에 `fitme_v2.captures`와 `fitme_v2.listings`를 만든다. 해당 스키마와 표를 미리 준비하면 런타임 계정에 DDL 권한이 없어도 된다.
4. 종료는 실행 창에서 Ctrl+C를 누른다. `localhost`의 매물 링크는 같은 PC에서 시연할 수 있다. 서로 다른 기기는 두 기기에서 접근할 수 있는 동일한 V2 주소가 필요하다.

스크립트는 팀 경로 `~/poc-size-ai`의 Python과 DB 설정을 재사용한다. 의존성이 추가로 필요할 때는 V2 전용 venv(`~/.local/share/fitme-v2/venv`)를 만든다. 팀 경로를 변경한 환경은 `FITME_TEAM_DIR`를 지정한다. V2 설정은 `web/.env.example`을 `web/.env`로 복사해서 작성한다. 기존 프로세스가 사용할 포트와 구분하려면 `APP_PORT`를 지정한다.

## Redis 및 워커

웹 프로세스는 API 요청을 Redis Streams에 기록하고 같은 요청 ID의 결과를 반환한다. DB 워커는 카탈로그·추천·매물 저장/조회를 처리한다. 미디어 워커는 의류 측정과 매물별 모델 읽기를 처리한다. 공유 링크에서 참조하는 매물 치수와 모델 식별자는 MySQL `fitme_v2`에 보관한다.

로컬 기본 설정에서는 웹과 두 워커가 같은 프로세스에서 실행된다. 별도 프로세스로 실행하려면 각 호스트에 동일한 `REDIS_URL`을 지정하고, 웹 호스트에서 `V2_EMBEDDED_WORKERS=false`로 실행한다.

```bash
# 각각 별도 터미널 또는 호스트에서 실행
V2_EMBEDDED_WORKERS=false bash web/run.sh web
bash web/run.sh db
bash web/run.sh media
```

워커는 같은 MySQL에 접속해야 한다. 미디어 워커에 `GARMENT_MEASUREMENT_URL`을 지정하면 판매자가 확인한 JPEG를 측정 VM으로 전달한다. VM은 `{"basis":"garment","unit":"cm","category":"상의","measurements":{"chest_width":55,"body_length":69}}` 형식으로 측정을 반환한다. 이 값은 연동 형식의 예시다. 실시간 연결이 없으면 사용자가 팀 결과 파일을 불러오거나 직접 측정한 값을 등록할 수 있다.

VM이 모델을 업로드한 뒤 응답에 상대 Blob 이름 `model_blob`을 추가하면, `GARMENT_BLOB_CONTAINER_URL`에 설정된 읽기용 Azure Blob 컨테이너에서 그 매물의 GLB를 가져온다. 이 설정에는 읽기용 SAS가 포함될 수 있으므로 미디어 워커에 보관한다.

판매자가 3D팀의 상품과 사이즈를 연결한 매물에서는 구매자가 로그인 후 본인의 사진·키·몸무게 전송에 동의하고 두 VM에 모델 생성을 요청할 수 있다. 일반 핏 비교는 키·몸무게만 입력한다. ⑧의 모델 ID와 링크는 Redis로 돌아오고, ⑨에서 브라우저가 신체·의류 Blob의 GLB와 기준점 JSON을 검증해 표시한다. [①~⑨ 순서와 VM·Blob 설정](docs/model-sequence.md) · [팀 소스의 실제 API 및 로그인 프록시 설정](../docs/3d/README.md)

## 체형 비교와 자료

키와 몸무게가 가까운 표본에 더 큰 가중치를 준다. 부위별 가중평균과 가중 표준편차 한 배로 계산한 **참고 범위**를 사용한다. 표본이 희박하거나 범위가 핏 구분선을 넘나들면 전체 핏을 보류한다. 상의는 가슴, 하의는 허리, 원피스는 가슴·허리를 확인하며, 잘 맞는 옷의 단면을 직접 넣은 경우에는 두 옷의 차이를 cm로 표시한다. 참고 범위와 핏 구분선의 적절성은 별도 착용 데이터로 검증해야 한다.

사이즈코리아의 28열 필터본에는 키와 둘레가 있으며 체중 열은 없다. 개인 ID로 체중 자료를 결합하고 단위·결측을 정리한 참조 파일을 준비해 DB 워커의 `SIZEKOREA_REFERENCE_CSV`로 지정하면 추천에 사용한다. 파일이 없으면 팀 DB 또는 설정된 데모 참고 표본을 사용한다. [자료 준비 및 분리 검증](docs/sizekorea.md)

V1 카탈로그 비교·배포 실험 안내는 개발용 비공개 레포의 `feature/front-test` 브랜치에 있다.
