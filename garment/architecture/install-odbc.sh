#!/bin/sh
# 역할: Azure SQL 연결에 필요한 Microsoft ODBC 드라이버를 설치합니다.
set -eu
. /etc/os-release
case "$ID:$VERSION_ID" in
    ubuntu:22.04|ubuntu:24.04) ;;
    *) echo "Expected Ubuntu 22.04 or 24.04" >&2; exit 1 ;;
esac
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl
curl -fsSL "https://packages.microsoft.com/config/ubuntu/$VERSION_ID/packages-microsoft-prod.deb" -o /tmp/fitme-ms-prod.deb
dpkg -i /tmp/fitme-ms-prod.deb
rm /tmp/fitme-ms-prod.deb
apt-get update
ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc
rm -rf /var/lib/apt/lists/*
