@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('Cognitive Services account name')
param cognitiveServicesAccountName string = ''

@description('API version for Cognitive Services operations')
param cognitiveServicesApiVersion string = '2023-05-01'

@description('OpenAI API version')
param openAiApiVersion string = '2024-10-01-preview'

@description('OpenAI 4o mini deployment name')
param openAi4oMiniDeploymentName string = ''

@description('OpenAI Realtime deployment name')
param openAiRealtimeDeploymentName string = ''

@description('The name of the Application Insights')
param applicationInsightsName string

@description('The name of the container apps environment')
param containerAppsEnvironmentName string

@description('Container Registry name')
param containerRegistryName string

@description('The name of the identity')
param identityName string

@description('The user-assigned role client id')
param userAssignedRoleClientId string

@description('The name of the image')
param imageName string = ''

@description('Container Port')
param containerPort int = 8765

@description('Specifies if the resource exists')
param exists bool

@description('Endpoint to send OTLP data to for observability')
param otlpEndpoint string

type managedIdentity = {
  resourceId: string
  clientId: string
}

@description('Unique identifier for user-assigned managed identity.')
param userAssignedManagedIdentity managedIdentity

@description('Name of the app')
param serviceName string = 'backend'

var azureOpenAiEndpoint = reference(resourceId('Microsoft.CognitiveServices/accounts', cognitiveServicesAccountName), cognitiveServicesApiVersion).endpoint

// Deploy Backend Voice Agent Container App
module backend '../core/host/container-app-upsert.bicep' = {
  name: 'backendContainerApp'
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
      'user-assigned-role-client-id': userAssignedRoleClientId
      'azure-openai-key': listKeys(resourceId('Microsoft.CognitiveServices/accounts', cognitiveServicesAccountName), cognitiveServicesApiVersion).key1
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
        name: 'AZURE_OPENAI_ENDPOINT'
        value: azureOpenAiEndpoint
      }      
      { 
        name: 'AZURE_OPENAI_API_VERSION'
        value: openAiApiVersion
      }
      { 
        name: 'AZURE_OPENAI_API_KEY' 
        secretRef: 'azure-openai-key' 
      }
      { 
        name: 'AZURE_OPENAI_4O_MINI_DEPLOYMENT'
        value: openAi4oMiniDeploymentName
      }
      { 
        name: 'AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME'
        value: openAiRealtimeDeploymentName 
      }
      {
        name: 'ASPIRE_DASHBOARD_ENDPOINT'
        value: otlpEndpoint
      }
    ]
    targetPort: containerPort
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = if (!empty(applicationInsightsName)) {
  name: applicationInsightsName
}

output SERVICE_BACKEND_IDENTITY_NAME string = identityName
output SERVICE_BACKEND_IMAGE_NAME string = backend.outputs.imageName
output SERVICE_BACKEND_NAME string = backend.outputs.name
output SERVICE_BACKEND_URI string = backend.outputs.uri
output SERVICE_BACKEND_PRINCIPAL_ID string = backend.outputs.principalId
