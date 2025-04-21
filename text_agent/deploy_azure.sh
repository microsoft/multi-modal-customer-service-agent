#!/bin/bash

# Variables
RESOURCE_GROUP="rg-analytic"
LOCATION="westus" # Change to your preferred location
CONTAINER_REGISTRY="analyticassistant"
CONTAINER_ENVIRONMENT="analytic-assistant-python-env"
AGENT_IMAGE="agent_service:latest"
STREAMLIT_IMAGE="streamlit_app:latest"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a container registry
az acr create --resource-group $RESOURCE_GROUP --name $CONTAINER_REGISTRY --sku Basic

# Enable admin rights for the container registry
az acr update -n $CONTAINER_REGISTRY --admin-enabled true

# Build the Python service image
az acr build --registry $CONTAINER_REGISTRY --image $AGENT_IMAGE --file ./Dockerfile.agent_service ./

# Build the Streamlit app image
az acr build --registry $CONTAINER_REGISTRY --image $STREAMLIT_IMAGE --file ./Dockerfile.streamlit_app ./

# Create a container environment
az containerapp env create --name $CONTAINER_ENVIRONMENT --resource-group $RESOURCE_GROUP --location $LOCATION
az acr update -n $CONTAINER_REGISTRY --admin-enabled true

# Deploy the analytic-assistant-python service and get its URL
agent_service_output=$(az containerapp create \
  --name analytic-assistant-python \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENVIRONMENT \
  --image $CONTAINER_REGISTRY.azurecr.io/$AGENT_IMAGE \
  --min-replicas 1 --max-replicas 1 \
  --target-port 8000 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Check if the deployment was successful and the URL was retrieved
if [ -z "$agent_service_output" ]; then
  echo "Failed to retrieve the URL of the analytic-assistant-python service."
  exit 1
fi

# Construct the agent_service_URL
agent_service_URL="https://$agent_service_output"

# Deploy the analytic-assistant-fe service with the agent_service_URL environment variable
fe_service_output=$(az containerapp create \
  --name analytic-assistant-fe \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENVIRONMENT \
  --image $CONTAINER_REGISTRY.azurecr.io/$STREAMLIT_IMAGE \
  --min-replicas 1 --max-replicas 1 \
  --target-port 8501 \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --env-vars agent_service_URL=$agent_service_URL \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Check if the deployment was successful
if [ -z "$fe_service_output" ]; then
  echo "Failed to deploy analytic-assistant-fe."
  exit 1
else
  echo "Successfully deployed analytic-assistant-fe with URL: http://$fe_service_output"
fi
