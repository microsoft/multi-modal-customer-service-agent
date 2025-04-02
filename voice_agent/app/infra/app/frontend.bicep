@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('Name of the app')
param serviceName string = 'frontend'

@description('The URL for the backend WebSocket connection')
param viteBackendWsUrl string

@description('The name of the Application Insights')
param applicationInsightsName string

@description('The name of the container apps environment')
param containerAppsEnvironmentName string

@description('Container Registry name')
param containerRegistryName string

@description('The name of the identity')
param identityName string

@description('The name of the image')
param imageName string = ''

@description('Specifies if the resource exists')
param exists bool

type managedIdentity = {
  resourceId: string
  clientId: string
}

@description('Unique identifier for user-assigned managed identity.')
param userAssignedManagedIdentity managedIdentity


module frontend '../core/host/container-app-upsert.bicep' = {
  name: 'frontendContainerApp'
  params: {
    name: serviceName
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: identityName
    imageName: imageName
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    secrets: {
      'azure-managed-identity-client-id':  userAssignedManagedIdentity.clientId
    }
    env: [
      {
        name: 'AZURE_MANAGED_IDENTITY_CLIENT_ID'
        value: 'azure-managed-identity-client-id'
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: !empty(applicationInsightsName) ? applicationInsights.properties.ConnectionString : ''
      }
      { 
        name: 'VITE_BACKEND_WS_URL'
        value: replace(viteBackendWsUrl, 'https', 'wss')
      }
    ]
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (!empty(applicationInsightsName)) {
  name: applicationInsightsName
}

output SERVICE_FRONTEND_IDENTITY_NAME string = identityName
output SERVICE_FRONTEND_IMAGE_NAME string = frontend.outputs.imageName
output SERVICE_FRONTEND_NAME string = frontend.outputs.name
output SERVICE_FRONTEND_URI string = frontend.outputs.uri
