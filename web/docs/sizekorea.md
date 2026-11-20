# V2 구매자 체형 참고 자료 준비

제공된 2020~2021년 성인 직접측정 필터본에는 키와 신체 둘레가 있고 체중 열이 없다. 동일 조사에서 같은 사람을 식별하는 `HUMAN_ID`와 실제 체중(kg)을 확보한 뒤 연결한다. 입력 CSV는 UTF-8이고 키·둘레·어깨사이너비는 mm 단위다. 원자료와 출력은 앱 정적 폴더 밖에 둔다.

```bash
python web/sizekorea_reference.py /data/private/sizekorea-filter.csv \
  /data/private/body-reference.csv --weights /data/private/weights-kg.csv
export SIZEKOREA_REFERENCE_CSV=/data/private/body-reference.csv
```

체중 파일의 헤더는 `HUMAN_ID,weight_kg`다. 체중이 입력 CSV에 이미 있으면 `--weights`를 생략한다. 체중 열 이름을 직접 지정하려면 `--weight-column`을 쓴다.

변환기는 ID를 기준으로 연결하고 중복 ID가 있으면 중단한다. 미매칭 인원과 필수값 결측 인원은 완료 시 집계한다. 빈칸과 `9999`는 결측값이며, 부위별 결측은 비워 둔다. 출력에는 키와 부위 치수(cm), 체중(kg)만 남는다. V2 추천 워커에서 이 파일을 읽을 수 있게 같은 경로를 연결하고 환경 변수를 설정한다. 워커가 Docker에서 실행되면 컨테이너에 읽기 전용으로 마운트한 경로를 사용한다.

설정된 파일을 읽을 수 없거나 규격이 다르면 추천이 자료 확인을 안내한다. 이 데이터로 측정 가능한 성능은 신체 치수의 추정 오차다. 의류의 실제 착용감은 별도 착용 기록으로 검증한다.

앱의 Python 환경에서 `python web/tools/evaluate_sizekorea.py /data/private/body-reference.csv`를 실행하면 고정된 난수 시드로 약 20%의 사람을 분리한 뒤 실제 V2 추정식으로 평가한다. 부위별 평균절대오차(cm)는 추정이 가능했던 사람만으로 계산하며, 보류 수를 함께 출력한다.
