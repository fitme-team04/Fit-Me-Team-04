# =====================================================================
# network.tf — 서브넷, NSG(입구 경비원), DB 연결 지점 이름 찾기(Private DNS)
# =====================================================================
#
# [비유로 보는 전체 그림]
#   VNet(fitme-vnet-dev)      = 건물 하나 (main.tf 에 이미 있음)
#   서브넷(snet-*)            = 건물의 층
#   NSG(fitme-nsg-*-dev)      = 각 층 입구의 경비원 (누구를, 몇 번 문으로 들여보낼지)
#   Private DNS               = 건물 안내 데스크 (DB 이름을 물으면 내부 주소를 알려줌)
#
# [층 배치]
#   snet-front 10.4.1.0/24 : 웹 VM (nginx + 프론트 + 백엔드). 바깥에 열린 유일한 층
#   snet-back  10.4.2.0/24 : 3D VM (8001 인체, 8002 의류)
#   snet-data  10.4.3.0/24 : DB 층 (Azure SQL 연결 지점 = Private Endpoint 가 들어감)
#
# [요금]
#   서브넷·NSG 는 무료, Private DNS 영역만 월 약 700원
#
# [권한]
#   이 파일은 역할 할당(IAM)을 하지 않아요.
#   → GitHub Actions용 계정의 Contributor 권한으로 충분해요 (Owner 필요 없음)
#
# [주의]
#   이 파일을 고친 PR 의 plan 결과에 "destroy" 나 "must be replaced" 가 보이면
#   머지하지 말고 멈추기 (지우고 다시 만든다는 뜻)
# =====================================================================


# ---------------------------------------------------------------------
# 입력값: SSH(22번 문)로 들어올 수 있는 IP 목록
# ---------------------------------------------------------------------
# - 학원·팀원 IP 를 여기에 적어요. 한 개짜리 IP 는 끝에 /32 를 붙여요.
#   예: default = ["203.0.113.10/32", "198.51.100.7/32"]
# - 비어 있으면([]) SSH 허용 규칙을 아예 안 만들어요 → 22번 문은 닫힌 상태
# - IP 가 바뀌면 이 목록만 고쳐서 PR 하면 돼요
variable "ssh_allowed_ips" {
  type = list(string)
  default = [
    "203.0.113.10/32",  # 예시 값 (팀원 A) — 실제 IP 는 공개 레포에 적지 않아요
    "198.51.100.7/32",  # 예시 값 (팀원 B)
  ]
}

# 층별 주소를 한곳에 모아 두고 아래에서 이름으로 불러 써요.
locals {
  cidr_front = "10.4.1.0/24"
  cidr_back  = "10.4.2.0/24"
  cidr_data  = "10.4.3.0/24"
}


# =====================================================================
# 1. 서브넷 (층 만들기)
# =====================================================================
# snet-front 는 main.tf 에 이미 있어서 여기선 back·data 만 만들어요.

# 3D VM 이 들어갈 층
resource "azurerm_subnet" "back" {
  name                 = "snet-back"
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [local.cidr_back]
}

# DB 층
# - 11/10 MySQL → Azure SQL 로 바꾸면서 "MySQL 전용" 표시(위임)를 뺐어요.
# - Azure SQL 서버 본체는 VNet 밖에 있고, 이 층에는 서버로 가는
#   "연결 지점"(Private Endpoint, 내부 주소 10.4.3.x 하나)만 들어와요.
# - 위임이 없어야 Private Endpoint 를 넣을 수 있어요.
resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [local.cidr_data]
}


# =====================================================================
# 2. NSG (층마다 경비원 1명)
# =====================================================================
# 규칙 읽는 법
#   priority  : 숫자가 작을수록 먼저 검사 (100 → 110 → ... → 4000)
#               처음 맞는 규칙에서 바로 결정되고 뒤 규칙은 안 봐요.
#   direction : Inbound = 들어오는 것 (나가는 건 기본값대로 허용)
#   access    : Allow 허용 / Deny 차단
#   source_*  : 어디서 오는지 ("Internet" = 바깥 전체, "10.4.1.0/24" = front 층)
#   destination_port_range : 몇 번 문인지 (443 HTTPS, 80 HTTP, 22 SSH, 1433 Azure SQL)
#
# 왜 모든 NSG 끝에 4000번 "deny-vnet-inbound" 가 있나?
#   Azure 에는 눈에 안 보이는 기본 규칙 "VNet 안끼리는 다 허용"(65000번)이 있어요.
#   그대로 두면 층을 나눈 의미가 없어서, 그 앞(4000번)에서 "나머지 VNet 안 접속은 차단"을 넣어요.
#   → 위에서 직접 허용한 것만 통과해요.
#
# 바깥(인터넷)에서 오는 나머지는 Azure 기본 규칙이 이미 막아 줘서 따로 안 적어요.


# ---- 2-1. front 층 경비원 (웹 VM) ----
resource "azurerm_network_security_group" "front" {
  name                = "fitme-nsg-front-dev"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.tags

  # 누구나 웹사이트(HTTPS)에 들어올 수 있게
  security_rule {
    name                       = "allow-https"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = "Internet"
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "443"
  }

  # HTTP 도 허용: http:// 로 온 사람을 https:// 로 넘기기 + 무료 인증서(Let's Encrypt) 발급용
  security_rule {
    name                       = "allow-http"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = "Internet"
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "80"
  }

  # SSH: 위 ssh_allowed_ips 에 적은 IP 만. 목록이 비면 이 규칙 자체가 안 생겨요.
  # (dynamic = "조건이 맞을 때만 이 블록을 만든다"는 Terraform 문법)
  dynamic "security_rule" {
    for_each = length(var.ssh_allowed_ips) > 0 ? [1] : []
    content {
      name                       = "allow-ssh-team"
      priority                   = 120
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_address_prefixes    = var.ssh_allowed_ips
      source_port_range          = "*"
      destination_address_prefix = "*"
      destination_port_range     = "22"
    }
  }

  # 다른 층(back·data)에서 웹 VM 으로 먼저 들어올 일은 없어서 막아요.
  security_rule {
    name                       = "deny-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_address_prefix      = "VirtualNetwork"
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "*"
  }
}


# ---- 2-2. back 층 경비원 (3D VM) ----
# 바깥에서는 아무것도 못 들어오고, front 층(웹 VM)에서 오는 것만 받아요.
resource "azurerm_network_security_group" "back" {
  name                = "fitme-nsg-back-dev"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.tags

  # 백엔드(웹 VM)가 3D 생성 요청을 보내는 문 (8001 인체, 8002 의류)
  security_rule {
    name                       = "allow-3d-from-front"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = local.cidr_front
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "8001-8002"
  }

  # SSH 는 웹 VM 을 거쳐서만: 노트북 → 웹 VM → 3D VM  (ssh -J 웹VM 3DVM)
  security_rule {
    name                       = "allow-ssh-from-front"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = local.cidr_front
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "22"
  }

  # 그 밖의 VNet 안 접속 차단
  security_rule {
    name                       = "deny-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_address_prefix      = "VirtualNetwork"
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "*"
  }
}


# ---- 2-3. data 층 경비원 (Azure SQL) ----
# DB 문(1433)은 백엔드가 있는 층에서만 열어요.
# 지금은 백엔드가 웹 VM 안(front 층)이라고 가정했어요.
# 백엔드를 back 층으로 옮기면 source_address_prefix 를 local.cidr_back 으로 바꾸면 돼요.
# 참고: Private Endpoint 에 NSG 가 적용되려면 서브넷의 "네트워크 정책"이 켜져 있어야 해요
#       (Terraform 기본값이 켜짐이라 따로 적을 필요 없어요).
resource "azurerm_network_security_group" "data" {
  name                = "fitme-nsg-data-dev"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.tags

  security_rule {
    name                       = "allow-sql-from-backend"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = local.cidr_front
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "1433"
  }

  # 3D VM 등 다른 층에서는 DB 접속 불가
  security_rule {
    name                       = "deny-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_address_prefix      = "VirtualNetwork"
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "*"
  }
}


# ---- 2-4. 경비원을 층에 배치하기 ----
# NSG 는 만들기만 하면 아무 데도 안 붙어 있어요. 아래가 "이 경비원은 이 층 담당" 연결이에요.
resource "azurerm_subnet_network_security_group_association" "front" {
  subnet_id                 = azurerm_subnet.front.id
  network_security_group_id = azurerm_network_security_group.front.id
}

resource "azurerm_subnet_network_security_group_association" "back" {
  subnet_id                 = azurerm_subnet.back.id
  network_security_group_id = azurerm_network_security_group.back.id
}

resource "azurerm_subnet_network_security_group_association" "data" {
  subnet_id                 = azurerm_subnet.data.id
  network_security_group_id = azurerm_network_security_group.data.id
}


# =====================================================================
# 3. Private DNS (건물 안내 데스크)
# =====================================================================
# 내부 전용 Azure SQL 은 VM 이 "<서버이름>.database.windows.net" 을 물으면
# 이 안내 데스크가 "10.4.3.x(연결 지점)로 가세요"라고 알려줘요.
#
# - 이름은 Azure 가 정해 둔 "privatelink.database.windows.net" 이어야 해요 (바꾸면 안 됨).
# - SQL 서버는 Portal 에서 만들고, Networking 탭 → Private endpoint 추가 →
#   서브넷 snet-data, Private DNS 는 이 영역을 골라요.
# - SQL 서버를 더 만들어도 이 영역 하나를 같이 써요.
resource "azurerm_private_dns_zone" "sql" {
  name                = "privatelink.database.windows.net"
  resource_group_name = data.azurerm_resource_group.rg.name
  tags                = local.tags
}

# 안내 데스크를 우리 건물(VNet)에 연결
# - registration_enabled = false : VM 이름은 자동 등록 안 함
resource "azurerm_private_dns_zone_virtual_network_link" "sql" {
  name                  = "link-fitme-vnet-dev-sql"
  resource_group_name   = data.azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.sql.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
  tags                  = local.tags
}


# =====================================================================
# 4. 출력값 (apply 후 GitHub Actions 로그에 표시돼요)
# =====================================================================
# 나중에 VM·SQL 연결 지점을 Terraform 으로 만들 때 이 값들을 써요.
output "subnet_back_id" {
  value = azurerm_subnet.back.id
}

output "subnet_data_id" {
  value = azurerm_subnet.data.id
}

output "sql_private_dns_zone" {
  value = azurerm_private_dns_zone.sql.name
}
