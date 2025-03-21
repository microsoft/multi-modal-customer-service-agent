#!/bin/bash  
  
# Variables  
RESOURCE_GROUP="rg-voiceagent"  
LOCATION="westus"  
CONTAINER_REGISTRY="voiceagentreg001"  
CONTAINER_ENVIRONMENT="voice-agent-env"  
  
# Dynamically versioned tags for the images (using a timestamp)  
TIMESTAMP=$(date +%Y%m%d%H%M%S)  
IMAGE_NAME="voice-agent:$TIMESTAMP"  
  
# Create a resource group (idempotent)  
az group create --name $RESOURCE_GROUP --location $LOCATION  
  
# Create a container registry (idempotent)  
az acr create --resource-group $RESOURCE_GROUP --name $CONTAINER_REGISTRY --sku Basic  
  
# Enable admin rights for the container registry  
az acr update --name $CONTAINER_REGISTRY --admin-enabled true --resource-group $RESOURCE_GROUP
  
# Build the Docker image and push it to the container registry  
az acr build --registry $CONTAINER_REGISTRY --image $IMAGE_NAME --file ./Dockerfile .
  
# Create a container environment if it does not already exist  
az containerapp env create \
  --name $CONTAINER_ENVIRONMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
  
# Function to deploy or update a container app  
deploy_container_app() {  
  local APP_NAME=$1  
  local IMAGE_NAME=$2  
  local PORT=$3  
  
  # Check if the container app already exists  
  APP_EXISTS=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query name --output tsv 2>/dev/null)  
  
  if [ -z "$APP_EXISTS" ]; then  
    # Deploy the container app (creation step only if it doesn't exist)  
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
  
    # Check if the deployment was successful  
    if [ -z "$service_output" ]; then  
      echo "Failed to deploy $APP_NAME."  
      exit 1  
    else  
      echo "Successfully deployed $APP_NAME service with URL: https://$service_output"  
    fi  
  else  
    # Update the container app with the new image if it already exists  
    az containerapp update \ 
      --name $APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --image $CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME
  
    # Fetch the service URL (optional validation)  
    service_output=$(az containerapp show \
      --name $APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --query properties.configuration.ingress.fqdn \
      --output tsv)
  
    if [ -z "$service_output" ]; then  
      echo "Failed to update $APP_NAME."  
      exit 1  
    else  
      echo "Successfully updated $APP_NAME service with URL: https://$service_output"  
    fi  
  fi  
}  
  
# Deploy/Update the application (translator-assistant)  
deploy_container_app "translator-assistant" $IMAGE_NAME 8765  