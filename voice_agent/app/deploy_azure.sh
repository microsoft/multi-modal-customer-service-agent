#!/bin/bash  
set -e  
set -o pipefail  

# Use first parameter as unique identifier for ACR, or default to "RANDOM"
IDENTIFIER="${1:-RANDOM}"

# Variables  
RESOURCE_GROUP="rgvoiceagent"  
LOCATION="westus"  
CONTAINER_REGISTRY="voiceagentreg001$IDENTIFIER"  
CONTAINER_ENVIRONMENT="voice-agent-env"  
APP_BACKEND=${2:-"ai-customer-service-backend"}  
APP_FRONTEND=${3:-"ai-customer-service-frontend"}  
BACKEND_PORT=8765  
FRONTEND_PORT=80  
  
# Use a timestamp-based tag for image uniqueness  
TIMESTAMP=$(date +%Y%m%d%H%M%S)  
BACKEND_IMAGE="backend:$TIMESTAMP"  
FRONTEND_IMAGE="frontend:$TIMESTAMP"  

# Validate prerequisites  
if ! command -v az &> /dev/null || ! az account show &> /dev/null; then  
  echo "Ensure Azure CLI, and Azure login are configured."  
  exit 1  
fi  
  
# Create resource group (idempotent)  
echo "Creating (or updating) resource group: $RESOURCE_GROUP..."  
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"  
  
# Create container registry (idempotent)  
echo "Creating (or updating) container registry: $CONTAINER_REGISTRY..."  
az acr create --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_REGISTRY" --sku Basic  
  
# Enable admin rights for the registry  
echo "Enabling admin rights for container registry: $CONTAINER_REGISTRY..."  
az acr update --name "$CONTAINER_REGISTRY" --admin-enabled true --resource-group "$RESOURCE_GROUP"  
  
# Log in to the container registry  
echo "Logging into container registry: $CONTAINER_REGISTRY..."  
az acr login --name "$CONTAINER_REGISTRY"  
  
# Build and push the Docker images for backend and frontend  
echo "Building and pushing backend Docker image: $BACKEND_IMAGE..."  
az acr build --registry "$CONTAINER_REGISTRY" --image "$BACKEND_IMAGE" --file backend/Dockerfile backend/

echo "Building and pushing frontend Docker image: $FRONTEND_IMAGE..." 
az acr build --registry "$CONTAINER_REGISTRY" --image "$FRONTEND_IMAGE" --file frontend/Dockerfile frontend/
  
# Ensure container environment exists (idempotency)  
echo "Checking if container environment $CONTAINER_ENVIRONMENT exists..."  
if ! az containerapp env show --name "$CONTAINER_ENVIRONMENT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then  
  echo "Container environment $CONTAINER_ENVIRONMENT not found. Creating it now..."  
  az containerapp env create --name "$CONTAINER_ENVIRONMENT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION"  
else  
  echo "Container environment $CONTAINER_ENVIRONMENT already exists. Proceeding..."  
fi  
  
# Retrieve ACR credentials (they will be needed for container app creation)  
ACR_USERNAME=$(az acr credential show --name "$CONTAINER_REGISTRY" --resource-group "$RESOURCE_GROUP" --query username --output tsv)  
ACR_PASSWORD=$(az acr credential show --name "$CONTAINER_REGISTRY" --resource-group "$RESOURCE_GROUP" --query passwords[0].value --output tsv)  
  
# Helper function to deploy (or update) a container app  
# EXTRA_ENV is an optional parameter (a string of KEY=VALUE pairs) that will be passed as --env-vars  
deploy_container_app() {  
  local APP_NAME="$1"  
  local IMAGE_NAME="$2"  
  local PORT="$3"  
  local EXTRA_ENV="$4"  
  
  echo "Checking if container app $APP_NAME exists..."  
  APP_EXISTS=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query name --output tsv 2>/dev/null || true)  

  if [ -z "$APP_EXISTS" ]; then  
    echo "Creating container app: $APP_NAME..."
    az containerapp create \
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
      --ingress external \
      ${EXTRA_ENV:+--env-vars "$EXTRA_ENV"} | { echo "Error: Failed to create container app $APP_NAME"; exit 1; }
    echo "Container app $APP_NAME created successfully."  
  else  
    echo "Updating container app: $APP_NAME..."
    az containerapp update \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --image "$CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME" \
      ${EXTRA_ENV:+--env-vars "$EXTRA_ENV"} || { echo "Error: Failed to update container app $APP_NAME"; exit 1; }  
    echo "Container app $APP_NAME updated successfully."  
  fi  
}  

# Extract environment variables from the backend .env file
BACKEND_EXTRA_ENV=$(grep -v '^\s*#' backend/.env | sed 's/\s*#.*//' | xargs)

# Deploy backend container app (with the extracted environment variables)  
deploy_container_app "$APP_BACKEND" "$BACKEND_IMAGE" "$BACKEND_PORT" "$BACKEND_EXTRA_ENV"  
  
# Give the backend a moment to start up (and for its ingress FQDN to be set)  
sleep 10  
  
# Retrieve the backend’s fully qualified domain name (FQDN)  
BACKEND_FQDN=$(az containerapp show --name "$APP_BACKEND" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" --output tsv)  
echo "Backend FQDN is: $BACKEND_FQDN"  
  
# Construct the WebSocket URL for the frontend  
# (Adjust the protocol scheme as needed – for example, ws:// versus wss://)  
FRONTEND_EXTRA_ENV="VITE_BACKEND_WS_URL=wss://$BACKEND_FQDN"  
echo "The frontend will receive: $FRONTEND_EXTRA_ENV as environment variable."  
  
# Deploy the frontend container app with the extra environment variable  
deploy_container_app "$APP_FRONTEND" "$FRONTEND_IMAGE" "$FRONTEND_PORT" "$FRONTEND_EXTRA_ENV"  
  
echo "Deployment complete!"  