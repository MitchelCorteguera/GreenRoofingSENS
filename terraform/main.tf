terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.1"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = "rg-greenroofing-sensors"
  location = "East US"
}

resource "azurerm_storage_account" "main" {
  name                     = "stgreenroofing${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                = azurerm_resource_group.main.location
  account_tier            = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_service_plan" "main" {
  name                = "asp-greenroofing-sensors"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  os_type            = "Linux"
  sku_name           = "Y1"
}

resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-greenroofing-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "sensor-data"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "main" {
  name                = "readings"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/deviceId"
}

resource "azurerm_linux_function_app" "main" {
  name                = "func-greenroofing-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  service_plan_id    = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key

  site_config {
    application_stack {
      python_version = "3.9"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "COSMOS_ENDPOINT" = azurerm_cosmosdb_account.main.endpoint
    "COSMOS_KEY" = azurerm_cosmosdb_account.main.primary_key
    "COSMOS_DATABASE" = azurerm_cosmosdb_sql_database.main.name
    "COSMOS_CONTAINER" = azurerm_cosmosdb_sql_container.main.name
  }
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.name}.azurewebsites.net"
}

output "function_endpoint" {
  value = "https://${azurerm_linux_function_app.main.name}.azurewebsites.net/api/sensor-data"
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
  sensitive = true
}