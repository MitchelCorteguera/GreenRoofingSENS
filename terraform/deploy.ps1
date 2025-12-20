# PowerShell deployment script for GreenRoofing sensor infrastructure

# Variables
$RG_NAME = "rg-greenroofing-sensors"
$LOCATION = "eastus"
$SUFFIX = -join ((1..8) | ForEach {Get-Random -input ([char[]]'abcdefghijklmnopqrstuvwxyz0123456789')})
$STORAGE_NAME = "stgreenroofing$SUFFIX"
$COSMOS_NAME = "cosmos-greenroofing-$SUFFIX"
$FUNCTION_NAME = "func-greenroofing-$SUFFIX"
$PLAN_NAME = "asp-greenroofing-sensors"

Write-Host "Creating infrastructure with suffix: $SUFFIX"

# Create Resource Group
az group create --name $RG_NAME --location $LOCATION

# Create Storage Account
az storage account create `
  --name $STORAGE_NAME `
  --resource-group $RG_NAME `
  --location $LOCATION `
  --sku Standard_LRS

# Create App Service Plan (Consumption)
az functionapp plan create `
  --name $PLAN_NAME `
  --resource-group $RG_NAME `
  --location $LOCATION `
  --sku Dynamic

# Create Cosmos DB Account
az cosmosdb create `
  --name $COSMOS_NAME `
  --resource-group $RG_NAME `
  --locations "regionName=$LOCATION failoverPriority=0" `
  --default-consistency-level Session

# Create Cosmos DB Database
az cosmosdb sql database create `
  --account-name $COSMOS_NAME `
  --resource-group $RG_NAME `
  --name sensor-data

# Create Cosmos DB Container
az cosmosdb sql container create `
  --account-name $COSMOS_NAME `
  --resource-group $RG_NAME `
  --database-name sensor-data `
  --name readings `
  --partition-key-path "/deviceId"

# Get Cosmos DB connection info
$COSMOS_ENDPOINT = az cosmosdb show --name $COSMOS_NAME --resource-group $RG_NAME --query documentEndpoint -o tsv
$COSMOS_KEY = az cosmosdb keys list --name $COSMOS_NAME --resource-group $RG_NAME --query primaryMasterKey -o tsv

# Create Function App
az functionapp create `
  --name $FUNCTION_NAME `
  --resource-group $RG_NAME `
  --plan $PLAN_NAME `
  --storage-account $STORAGE_NAME `
  --runtime python `
  --runtime-version 3.9 `
  --os-type Linux

# Configure Function App Settings
az functionapp config appsettings set `
  --name $FUNCTION_NAME `
  --resource-group $RG_NAME `
  --settings `
    FUNCTIONS_WORKER_RUNTIME=python `
    COSMOS_ENDPOINT=$COSMOS_ENDPOINT `
    COSMOS_KEY=$COSMOS_KEY `
    COSMOS_DATABASE=sensor-data `
    COSMOS_CONTAINER=readings

Write-Host "Deployment complete!"
Write-Host "Function App URL: https://$FUNCTION_NAME.azurewebsites.net"
Write-Host "Function Endpoint: https://$FUNCTION_NAME.azurewebsites.net/api/sensor-data"
Write-Host "Cosmos Endpoint: $COSMOS_ENDPOINT"