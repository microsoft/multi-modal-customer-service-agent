#!/bin/bash  
set -e  
set -o pipefail  
  
# Variables  
RESOURCE_GROUP="rgvoiceagent"  
LOCATION="westus"  
CONTAINER_REGISTRY="voiceagentreg001"  
CONTAINER_ENVIRONMENT="voice-agent-env"  
APP_BACKEND=${1:-"ai-customer-service-backend"}  
APP_FRONTEND=${2:-"ai-customer-service-frontend"}  
BACKEND_PORT=8765  
FRONTEND_PORT=80  
  
TIMESTAMP=$(date +%Y%m%d%H%M%S)  
BACKEND_IMAGE="backend:$TIMESTAMP"  
FRONTEND_IMAGE="frontend:$TIMESTAMP"  
  
# Validate prerequisites  
if ! command -v az &> /dev/null || ! command -v docker &> /dev/null || ! az account show &> /dev/null; then  
    echo "Ensure Azure CLI, Docker, and Azure login are configured."  
    exit 1  
fi  
  
# Create or update resource group  
echo "Creating (or updating) resource group: $RESOURCE_GROUP..."  
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"  
  
# Create or update container registry  
echo "Creating (or updating) container registry: $CONTAINER_REGISTRY..."  
az acr create --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_REGISTRY" --sku Basic  
  
# Enable admin rights for container registry  
echo "Enabling admin rights for container registry: $CONTAINER_REGISTRY..."  
az acr update --name "$CONTAINER_REGISTRY" --admin-enabled true --resource-group "$RESOURCE_GROUP"  
  
# Login to container registry  
echo "Logging into container registry: $CONTAINER_REGISTRY..."  
az acr login --name "$CONTAINER_REGISTRY"  
  
# Build and push backend Docker image  
echo "Building and pushing backend Docker image: $BACKEND_IMAGE..."  
az acr build --registry "$CONTAINER_REGISTRY" --image "$BACKEND_IMAGE" --file Dockerfile.backend .  
  
# Build and push frontend Docker image  
echo "Building and pushing frontend Docker image: $FRONTEND_IMAGE..."  
az acr build --registry "$CONTAINER_REGISTRY" --image "$FRONTEND_IMAGE" --file Dockerfile.frontend .  
  
# Ensure container environment exists  
echo "Checking if container environment $CONTAINER_ENVIRONMENT exists..."  
if ! az containerapp env show --name "$CONTAINER_ENVIRONMENT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then  
    echo "Container environment $CONTAINER_ENVIRONMENT not found. Creating it now..."  
    az containerapp env create --name "$CONTAINER_ENVIRONMENT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"  
else  
    echo "Container environment $CONTAINER_ENVIRONMENT already exists."  
fi  
  
# Function to deploy or update a container app  
deploy_container_app() {  
    local APP_NAME="$1"  
    local IMAGE_NAME="$2"  
    local PORT="$3"  
  
    echo "Checking if container app $APP_NAME exists..."  
    APP_EXISTS=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query name --output tsv 2>/dev/null)  
  
    # Retrieve ACR credentials  
    ACR_USERNAME=$(az acr credential show --name "$CONTAINER_REGISTRY" --resource-group "$RESOURCE_GROUP" --query username --output tsv)  
    ACR_PASSWORD=$(az acr credential show --name "$CONTAINER_REGISTRY" --resource-group "$RESOURCE_GROUP" --query passwords[0].value --output tsv)  
  
    if [ -z "$APP_EXISTS" ]; then  
        echo "Creating container app: $APP_NAME..."  
        if ! az containerapp create \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --environment "$CONTAINER_ENVIRONMENT" \
            --image "$CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME" \
            --min-replicas 1 \
            --max-replicas 1 \
            --target-port "$PORT" \
            --registry-server "$CONTAINER_REGISTRY.azurecr.io" \
            --registry-username "$ACR_USERNAME" \
            --registry-password "$ACR_PASSWORD" \
            --ingress external; then
            echo "Error: Failed to create container app $APP_NAME."  
            exit 1  
        fi  
        echo "Container app $APP_NAME created successfully."  
    else  
        echo "Updating container app: $APP_NAME..."  
        if ! az containerapp update \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --image "$CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME"; then
            echo "Error: Failed to update container app $APP_NAME."  
            exit 1  
        fi  
        echo "Container app $APP_NAME updated successfully."  
    fi  
}  
  
# Deploy backend and frontend container apps  
deploy_container_app "$APP_BACKEND" "$BACKEND_IMAGE" "$BACKEND_PORT"  
deploy_container_app "$APP_FRONTEND" "$FRONTEND_IMAGE" "$FRONTEND_PORT"  