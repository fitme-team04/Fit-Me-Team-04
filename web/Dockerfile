# =====================================================================
# web/Dockerfile — 입어봄(Fit Me) 프론트 웹앱 이미지 만들기
# ---------------------------------------------------------------------
# 무엇을 만드나?
#   FastAPI 웹앱(web/) + 화면 파일(web/static) + 팀 추천 코드 5개를 담은
#   Docker 이미지. 웹 VM(fitme-vm-web-dev)에서 이 이미지로 컨테이너를 띄운다.
#
# 누가 쓰나?
#   GitHub Actions(.github/workflows/front-deploy.yml)가 dev에 코드가
#   들어올 때마다 이 파일로 이미지를 만들어 ACR(fitmeacrdev)에 올린다.
#
# 빌드 위치: 레포 최상위 (web/ 와 db/ 가 둘 다 보여야 함)
#   docker build -f web/Dockerfile -t fitmeacrdev.azurecr.io/fitme-web:<태그> .
#
# 이미지에 넣지 않는 것: .env 등 비밀값 (웹 VM의 /opt/fitme-web/app.env 로 따로 넣음)
# =====================================================================

# 1) 바탕 이미지: Python 3.12 가벼운 버전 (프론트 코드가 3.12 기준)
FROM python:3.12-slim

# 2) 파이썬 기본 설정
#    PYTHONDONTWRITEBYTECODE=1 : .pyc 캐시 파일을 만들지 않음 (이미지 깔끔하게)
#    PYTHONUNBUFFERED=1        : 로그가 바로바로 보이게 (docker compose logs 에서 확인)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3) 컨테이너 안 작업 폴더 (main.py 가 있는 곳)
WORKDIR /app

# 4) 파이썬 패키지 설치
#    requirements.txt 만 먼저 복사해서 설치 → 코드만 바뀌었을 땐 이 단계를
#    다시 하지 않아 빌드가 빨라짐 (Docker 캐시)
COPY web/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 5) 웹앱 코드와 화면 파일 복사 (web/ 폴더 전체)
COPY web/ /app/

# 6) 팀 추천 코드 5개 복사
#    web/team_bridge.py 가 web/team_code/ 폴더에서 이 파일들을 찾아 씀
#    (web/deploy/azure_deploy.sh 가 하던 방식과 같음)
COPY db/예시_코드/_db.py db/예시_코드/_추천.py db/예시_코드/_추정.py db/예시_코드/_검증.py db/예시_코드/_body_type.py /app/team_code/

# 6-1) 팀 사이즈 판정 기준(ease_check) 복사
#    web/ease_rules.py 가 /app/ease_check.py 를 찾아 씀. 없으면 판정이 모두 "판정할 수 없습니다"가 됨
COPY ml/ease_check/ease_check.py /app/ease_check.py

# 7) 보안 정리
#    - 혹시 섞여 들어온 .env 삭제 (비밀값은 이미지에 절대 넣지 않음)
#    - root 가 아닌 일반 사용자(fitme)로 실행 → 앱이 털려도 피해를 줄임
RUN rm -f /app/.env && useradd --uid 10002 --create-home fitme
USER fitme

# 8) 웹앱이 듣는 포트 (웹 VM 의 nginx 가 127.0.0.1:8766 으로 연결)
EXPOSE 8766

# 9) 컨테이너가 켜질 때 실행할 명령: uvicorn 으로 FastAPI 웹앱 시작
#    0.0.0.0 = 컨테이너 안 모든 주소에서 받기 (밖으로 열리는 건 compose 의 127.0.0.1 설정이 막아 줌)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8766"]
