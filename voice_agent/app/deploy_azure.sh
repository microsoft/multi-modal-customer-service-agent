#!/bin/bash  
  
# Enable command tracing for debugging  
set -e  
set -o pipefail  
  
# Variables  
RESOURCE_GROUP="rgvoiceagent"  
LOCATION="westus"  
CONTAINER_REGISTRY="voiceagentreg001"  
CONTAINER_ENVIRONMENT="voice-agent-env"  
APP_NAME=${1:-"ai-customer-service"}  
PORT=${2:-8765}  
  
# Timestamp-based image tagging  
TIMESTAMP=$(date +%Y%m%d%H%M%S)  
IMAGE_NAME="voice-agent:$TIMESTAMP"  
  
# Validate prerequisites  
if ! command -v az &> /dev/null || ! command -v docker &> /dev/null || ! az account show &> /dev/null; then  
  echo "Ensure Azure CLI, Docker, and Azure login are configured."  
  exit 1  
fi  
  
# Create resource group (idempotent)  
az group create --name $RESOURCE_GROUP --location $LOCATION  
  
# Create container registry (idempotent)  
az acr create --resource-group $RESOURCE_GROUP --name $CONTAINER_REGISTRY --sku Basic  
  
# Enable admin rights for the container registry  
az acr update --name $CONTAINER_REGISTRY --admin-enabled true --resource-group $RESOURCE_GROUP  
  
# Log in to the container registry  
az acr login --name $CONTAINER_REGISTRY  
  
# Build the Docker image and push it to the container registry  
az acr build --registry $CONTAINER_REGISTRY --image $IMAGE_NAME --file ./Dockerfile .  
  
# Create container environment (idempotent)  
az containerapp env create --name $CONTAINER_ENVIRONMENT --resource-group $RESOURCE_GROUP --location $LOCATION  
  
# Deploy or update container app  
deploy_container_app() {  
  local APP_NAME=$1  
  local IMAGE_NAME=$2  
  local PORT=$3  
  
  APP_EXISTS=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query name --output tsv 2>/dev/null)  
  
  if [ -z "$APP_EXISTS" ]; then  
    # Deploy the container app  
    service_output=$(az containerapp create \
      --name $APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --environment $CONTAINER_ENVIRONMENT \
      --image $CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME \
      --min-replicas 1 \
      --max-replicas 1 \
      --target-port $PORT \
      --ingress external \
      --query properties.configuration.ingress.fqdn \
      --output tsv)
  
    if [ -z "$service_output" ]; then  
      echo "Failed to deploy $APP_NAME."  
      exit 1  
    else  
      echo "Successfully deployed $APP_NAME service with URL: http://$service_output"  
    fi  
  else  
    # Update the container app  
    az containerapp update \  
      --name $APP_NAME \  
      --resource-group $RESOURCE_GROUP \  
      --image $CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME  
  
    service_output=$(az containerapp show \  
      --name $APP_NAME \  
      --resource-group $RESOURCE_GROUP \  
      --query properties.configuration.ingress.fqdn \  
      --output tsv)  
  
    if [ -z "$service_output" ]; then  
      echo "Failed to update $APP_NAME."  
      exit 1  
    else  
      echo "Successfully updated $APP_NAME service with URL: http://$service_output"  
    fi  
  fi  
}  
  
# Deploy or update the application  
deploy_container_app $APP_NAME $IMAGE_NAME $PORT  