#!/bin/bash

# Azure CLI deployment script for GreenRoofing sensor infrastructure
# Mirrors the Terraform configuration

# Variables (override with env vars if needed)
: "${LOCATION:=eastus}"
: "${SUFFIX:=$(openssl rand -hex 4)}"
: "${RG_NAME:=rg-greenroofing-sensors-${SUFFIX}}"
: "${PYTHON_VERSION:=3.11}"
: "${STORAGE_NAME:=stgreenroofing${SUFFIX}}"
: "${COSMOS_NAME:=cosmos-greenroofing-${SUFFIX}}"
: "${FUNCTION_NAME:=func-greenroofing-${SUFFIX}}"

echo "Creating infrastructure with suffix: ${SUFFIX}"
echo "Resource Group: ${RG_NAME}"
echo "Python version: ${PYTHON_VERSION}"

# Create Resource Group
az group create --name "$RG_NAME" --location "$LOCATION"

# Create Storage Account
az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RG_NAME" \
  --location "$LOCATION" \
  --sku Standard_LRS

# Create Function App on Linux Consumption plan (Azure auto-provisions the plan)
az functionapp create \
  --name "$FUNCTION_NAME" \
  --resource-group "$RG_NAME" \
  --consumption-plan-location "$LOCATION" \
  --storage-account "$STORAGE_NAME" \
  --runtime python \
  --runtime-version "$PYTHON_VERSION" \
  --functions-version 4 \
  --os-type Linux

# Create Cosmos DB Account
az cosmosdb create \
  --name "$COSMOS_NAME" \
  --resource-group "$RG_NAME" \
  --locations regionName="$LOCATION" failoverPriority=0 \
  --default-consistency-level Session

# Create Cosmos DB Database
az cosmosdb sql database create \
  --account-name "$COSMOS_NAME" \
  --resource-group "$RG_NAME" \
  --name sensor-data

# Create Cosmos DB Container
az cosmosdb sql container create \
  --account-name "$COSMOS_NAME" \
  --resource-group "$RG_NAME" \
  --database-name sensor-data \
  --name readings \
  --partition-key-path "/deviceId"

# Get Cosmos DB connection info
COSMOS_ENDPOINT=$(az cosmosdb show --name "$COSMOS_NAME" --resource-group "$RG_NAME" --query documentEndpoint -o tsv)
COSMOS_KEY=$(az cosmosdb keys list --name "$COSMOS_NAME" --resource-group "$RG_NAME" --query primaryMasterKey -o tsv)

# Configure Function App Settings
az functionapp config appsettings set \
  --name "$FUNCTION_NAME" \
  --resource-group "$RG_NAME" \
  --settings \
    FUNCTIONS_WORKER_RUNTIME=python \
    COSMOS_ENDPOINT=$COSMOS_ENDPOINT \
    COSMOS_KEY=$COSMOS_KEY \
    COSMOS_DATABASE=sensor-data \
    COSMOS_CONTAINER=readings

echo "Deployment complete!"
echo "Function App URL: https://${FUNCTION_NAME}.azurewebsites.net"
echo "Function Endpoint: https://${FUNCTION_NAME}.azurewebsites.net/api/sensor-data"
echo "Cosmos Endpoint: $COSMOS_ENDPOINT"
