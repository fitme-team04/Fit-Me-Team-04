> Current policy: normalized measures only for tops; brand tables only for bottom selection/fit; pants geometry is static. See garment-generation-policy.md. The inspection history below predates this policy.

# 신체 둘레와 핏 판정 API

## 신체 서버

`POST /api/avatars`의 성공 응답 최상위에 아래 세 필드를 추가합니다. 값은 Blender로 변형된 신체의 재측정치가 아니라 ML 예측 `male`의 원래 값입니다. 기존 `status`, `model_id`, `urls`는 유지합니다.

```json
{
  "status": "ready",
  "model_id": "기존 모델 해시",
  "urls": {"model.glb": "기존 다운로드 URL"},
  "chest_girth_cm": 100.1,
  "waist_girth_cm": 80.2,
  "hip_girth_cm": 96.3
}
```

숫자는 설명용 예시입니다. 신체 생성에 실패하면 원래 HTTP 상태 코드와 `detail`을 유지하고 세 둘레 모두 `null`로 반환합니다. 요청 검증 422, SAM·Blender·Blob 오류, 인증·과부하 오류, 처리되지 않은 500도 같은 방식입니다. 실패 전에 ML 예측이 완료됐더라도 둘레를 보내지 않습니다.

## 의류 서버

`POST /fit`은 다음 JSON을 받습니다. 기존 서버와 같은 `X-FitMe-Subject` 인증 헤더가 필요합니다. 둘레는 생략하거나 `null`로 보낼 수 있으며 이 경우 판정 엔진에서 판정 불가를 처리합니다.

```json
{
  "item_code": "실제 상품 코드",
  "size_label": "M",
  "chest_girth_cm": 100.1,
  "waist_girth_cm": 80.2,
  "hip_girth_cm": 96.3
}
```

서버 호출 순서:

1. `ease_check.MEASURES_SQL`을 상품 코드 매개변수로 실행해 모든 사이즈 단면을 조회합니다.
2. `sizes_from_db_rows(rows)`가 KR 사이즈의 단면을 둘레로 변환합니다.
3. 별도 상품·사이즈 조회로 실측 행이 없는 KR 사이즈도 빈 치수로 포함합니다. 임의의 기본 실측을 채우지 않습니다.
4. `check_all_sizes(category, body, sizes, size_label)`의 결과를 수정 없이 반환합니다.

반환 구조는 원본 판정 모듈 그대로입니다. **`verdict`, `message_ko`, `parts`는 `selected` 안에 있습니다.**

```json
{
  "selected": {
    "verdict": "FIT",
    "message_ko": "입을 수 있습니다. 가슴둘레 여유 +5.9cm",
    "category": "top",
    "size_label": "M",
    "ease_min_cm": 3.0,
    "parts": [],
    "rules_version": "ease-2026-11-16.v3"
  },
  "fit_sizes": ["M"],
  "recommended_size": "M",
  "all_sizes": [],
  "rules_version": "ease-2026-11-16.v3"
}
```

위 배열과 메시지는 구조 설명용으로 생략·예시 처리했습니다. 실제 응답에는 엔진이 계산한 부위·모든 사이즈 결과가 담깁니다. 몸 또는 옷 치수가 누락되면 `selected.verdict=UNDETERMINED`, `message_ko`는 “판정할 수 없습니다”로 시작합니다. 상품이 없으면 404, 선택 사이즈가 KR 목록에 없거나 카테고리가 잘못됐으면 422입니다. 추천·판정은 3D 생성과 독립적이며 하의 판정에는 허리·엉덩이 단면만 필요합니다. 하의 3D 생성의 필수 치수 7개와 다릅니다.

## 배포와 출처

`src/ease_check.py`는 로컬 원격 추적 브랜치 `origin/feature/ease-check`의 `e201b59`에서 가져온 원본 구현입니다. 현재 작업 브랜치에는 최상위 `ease_check/`가 없었으므로 해당 브랜치를 변경·삭제하지 않고 필요한 모듈만 의류 배포 경로에 포함했습니다. `Dockerfile`의 기존 `COPY src/ ./`로 API와 모듈이 함께 배포되며 새 외부 의존성은 없습니다. 판정 규칙의 출처·운영값 설명은 `ease-check-rules.md`를 참고합니다.

이번 범위는 두 서버 API입니다. 웹의 `web/model_pair.py`는 수신 영수증에서 모델 링크를 선별하므로 웹에서 이 세 필드를 사용하려면 별도로 전달해야 합니다. Azure DB에 실측을 삽입하거나 웹의 `/fit` 호출을 추가한 작업은 아닙니다. 실제 Azure 접속 없이 DB 모의 및 API 회귀 테스트로 검증했습니다.


Current SQL integration: /fit falls back to the three brand size tables for products absent from garment.garments. See sql-catalog-integration.md for inspected schema, circumference conversion and exact size-label selection.
