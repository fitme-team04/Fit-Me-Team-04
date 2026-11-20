# Fit Me 인프라 (Terraform)
# - 실행: GitHub Actions(.github/workflows/terraform.yml)가 PR에서 plan, main 반영 시 apply
# - 상태 기록(tfstate): Azure Storage Account 의 tfstate 컨테이너
# - 로그인: GitHub Actions용 계정 fitme-github-actions (OIDC, 리소스 그룹 Contributor)
#   → 역할 할당(권한 주기)은 이 코드에 넣지 않고 Portal에서 직접 해요.

terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "11ai-p1-team04-rg"
    storage_account_name = "fitmetfstatedev"
    container_name       = "tfstate"
    key                  = "fitme.tfstate"
    use_oidc             = true
  }
}

provider "azurerm" {
  features {}
  use_oidc = true
  # 구독 단위 작업(리소스 공급자 등록)은 권한이 없어서 끕니다.
  resource_provider_registrations = "none"
}

# 리소스 그룹은 이미 있으니 만들지 않고 읽어오기만 해요.
data "azurerm_resource_group" "rg" {
  name = "11ai-p1-team04-rg"
}

locals {
  tags = {
    project = "fitme"
    env     = "dev"
    owner   = "infra"
  }
}

# 테스트: VNet 1개 + 서브넷 1개 (VNet·서브넷은 요금 없음)
resource "azurerm_virtual_network" "main" {
  name                = "fitme-vnet-dev"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  address_space       = ["10.4.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "front" {
  name                 = "snet-front"
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.4.1.0/24"]
}

output "vnet_id" {
  value = azurerm_virtual_network.main.id
}

output "subnet_front_id" {
  value = azurerm_subnet.front.id
}
