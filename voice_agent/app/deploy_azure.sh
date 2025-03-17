#!/bin/bash  
  
# Variables  
RESOURCE_GROUP="rg-voice-agent"  
LOCATION="westus"  # Change to your preferred location  
CONTAINER_REGISTRY="voiceagentregistry"  
CONTAINER_ENVIRONMENT="voice-agent-env"  
IMAGE_NAME="voice-agent:latest"  
  
# Create a resource group  
az group create --name $RESOURCE_GROUP --location $LOCATION  
  
# Create a container registry  
az acr create --resource-group $RESOURCE_GROUP --name $CONTAINER_REGISTRY --sku Basic  
  
# Enable admin rights for the container registry  
az acr update -n $CONTAINER_REGISTRY --admin-enabled true  
  
# Log in to the container registry  
az acr login --name $CONTAINER_REGISTRY  
  
# Build the Docker image and push it to the container registry  
az acr build --registry $CONTAINER_REGISTRY --image $IMAGE_NAME --file ./Dockerfile .  
  
# Create a container environment  
az containerapp env create --name $CONTAINER_ENVIRONMENT --resource-group $RESOURCE_GROUP --location $LOCATION
# Deploy the application and get its URL  
app_service_output=$(az containerapp create \
  --name translator-assistant \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENVIRONMENT \
  --image $CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME \
  --min-replicas 1 --max-replicas 1 \
  --target-port 8765 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
  
# Check if the deployment was successful and the URL was retrieved  
if [ -z "$app_service_output" ]; then
  echo "Failed to retrieve the URL of the translator-assistant service."
  exit 1
else
  echo "Successfully deployed translator-assistant with URL: https://$app_service_output"
fi