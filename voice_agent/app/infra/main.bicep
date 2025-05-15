targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

@description('Name of the Azure Application Insights dashboard')
param applicationInsightsDashboardName string = ''

@description('Name of the Azure Application Insights resource')
param applicationInsightsName string = ''

@description('Name of the aspire dashboard container app')
param aspireDashboardName string = 'aspire-dashboard'

@description('Target port for the Aspire dashboard')
param aspireDashboardTargetPort int = 18888

@description('Image name for the Aspire dashboard')
param aspireDashboardImageName string = 'mcr.microsoft.com/dotnet/aspire-dashboard:9.0'

@description('Exposed port for Aspire dashboard additional endpoint for gRPC')
param aspireDashboardAdditionalGrpcExposedPort int = 18889

@description('Target port for Aspire dashboard additional endpoint for gRPC')
param aspireDashboardAdditionalGrpcTargetPort int = 18889

@description('Exposed port for Aspire dashboard additional endpoint for HTTP')
param aspireDashboardAdditionalHttpExposedPort int = 18890

@description('Target port for Aspire dashboard additional endpoint for HTTP')
param aspireDashboardAdditionalHttpTargetPort int = 18890

@description('Name of the Azure Log Analytics workspace')
param logAnalyticsName string = ''

@description('Name of the container apps environment')
param containerAppsEnvironmentName string = ''

@description('Name of the Azure container registry')
param containerRegistryName string = ''

@description('Name of the resource group for the Azure container registry')
param containerRegistryResourceGroupName string = ''

@description('Name of the frontend container app')
param frontendContainerAppName string = 'frontend'

@description('Name of the backend container app')
param backendContainerAppName string = 'backend'

@description('Name of the frontend image')
param frontendImageName string = ''

@description('Name of the backend image')
param backendImageName string = ''

// Tags that should be applied to all resources.
// 
// Note that 'azd-service-name' tags should be applied separately to service host resources.
// Example usage:
//   tags: union(tags, { 'azd-service-name': <service name in azure.yaml> })
var tags = {
  'azd-env-name': environmentName
}

@description('Name of the storage account')
param storageAccountName string = ''

@description('Name of the storage container. Default: content')
param storageContainerName string = 'content'

@description('Location of the resource group for the storage account')
param storageResourceGroupLocation string = location

@description('Name of the resource group for the storage account')
param storageResourceGroupName string = ''

@description('Specifies if the backend app exists')
param backendExists bool = false

@description('Specifies if the frontend app exists')
param frontendExists bool = false

@description('ID of the principal')
param principalId string = ''

@description('Type of the principal. Valid values: User,ServicePrincipal')
param principalType string = 'User'

@description('Name of the resource group for the OpenAI resources')
param openAiResourceGroupName string = ''

// Add virtual network parameters
@description('Name of the virtual network')
param vnetName string = ''

@description('Address prefix for the virtual network')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Name for the infrastructure subnet')
param infrastructureSubnetName string = 'infrastructure-subnet'

@description('Address prefix for the infrastructure subnet')
param infrastructureSubnetPrefix string = '10.0.0.0/23'

@description('Name for the Container Apps subnet')
param containerAppsSubnetName string = 'containerapps-subnet'

@description('Address prefix for the Container Apps subnet')
param containerAppsSubnetPrefix string = '10.0.2.0/23'

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: environmentName
  location: location
  tags: tags
}

resource storageResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(storageResourceGroupName)) {
  name: !empty(storageResourceGroupName) ? storageResourceGroupName : resourceGroup.name
}

resource azureOpenAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

// Create networking resources
module networking './core/host/networking.bicep' = {
  name: 'networking'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    vnetName: !empty(vnetName) ? vnetName : '${abbrs.networkVirtualNetworks}${resourceToken}'
    vnetAddressPrefix: vnetAddressPrefix
    infrastructureSubnetName: infrastructureSubnetName
    infrastructureSubnetPrefix: infrastructureSubnetPrefix
    containerAppsSubnetName: containerAppsSubnetName
    containerAppsSubnetPrefix: containerAppsSubnetPrefix
  }
}

// Create a user assigned identity
module identity './core/security/user-assigned-identity.bicep' = {
  name: 'identity'
  scope: resourceGroup
  params: {
    name: 'voice-agent-app-identity'
  }
}

// Monitor application with Azure Monitor
module monitoring './core/monitor/monitoring.bicep' = {
  name: 'monitoring'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    includeApplicationInsights: true
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: !empty(applicationInsightsDashboardName) ? applicationInsightsDashboardName : '${abbrs.portalDashboards}${resourceToken}'    
  }
}

// Container apps host (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    containerAppsEnvironmentName: !empty(containerAppsEnvironmentName) ? containerAppsEnvironmentName : '${abbrs.appManagedEnvironments}${resourceToken}'
    containerRegistryName: !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
    containerRegistryResourceGroupName: !empty(containerRegistryResourceGroupName) ? containerRegistryResourceGroupName : resourceGroup.name
    location: location
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
    // Pass the subnet ID to the container apps module
    infrastructureSubnetId: networking.outputs.infrastructureSubnetId
  }
}

module aiServices './core/ai/ai-services.bicep' = {
  name: 'ai-services'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    foundryHubName: '${abbrs.machineLearningServicesWorkspaces}${resourceToken}'
    applicationInsightsResourceId: monitoring.outputs.applicationInsightsId
    cognitiveServicesAccountName: '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    gpt4oDeploymentName: 'gpt-4o'
    gpt4oModelName: 'gpt-4o'
    gpt4oModelVersion: '2024-05-13'
    realtimeModelDeploymentName: 'gpt-4o-realtime-preview'
    embeddingModelDeploymentName: 'text-embedding-ada-002'
    gpt4oMiniModelDeploymentName: 'gpt-4o-mini'
    aiFoundryProjectName: '${abbrs.machineLearningServicesWorkspaces}${resourceToken}-project'
    aiFoundryProjectDisplayName: 'Voice Agent Multi Modal Workshop'
    abbrs: abbrs
  }
}

// Deploy individual container apps
module backendApp './app/backend.bicep' = {
  name: 'backend'
  scope: resourceGroup
  params: {
    serviceName: !empty(backendContainerAppName) ? backendContainerAppName : '${abbrs.appContainerApps}-back-${resourceToken}'
    location: location
    tags: tags
    imageName: backendImageName
    identityName: identity.outputs.name
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    userAssignedManagedIdentity: {
      resourceId: identity.outputs.resourceId
      clientId: identity.outputs.clientId
    }
    userAssignedRoleClientId: identity.outputs.clientId
    exists: backendExists
    cognitiveServicesAccountName: aiServices.outputs.cognitiveServicesAccountName
    openAi4oMiniDeploymentName: aiServices.outputs.gpt4oMiniModelDeploymentName
    openAiRealtimeDeploymentName: aiServices.outputs.realtimeModelDeploymentName
    otlpEndpoint: 'http://${aspireDashboardName}:${aspireDashboardAdditionalGrpcExposedPort}/' // send grpc with http as the transport
  }
}

module frontendApp './app/frontend.bicep' = {
  name: 'frontend'
  scope: resourceGroup
  params: {
    serviceName: !empty(frontendContainerAppName) ? frontendContainerAppName : '${abbrs.appContainerApps}-front-${resourceToken}'
    location: location
    tags: tags
    imageName: frontendImageName
    identityName: identity.outputs.name
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    userAssignedManagedIdentity: {
      resourceId: identity.outputs.resourceId
      clientId: identity.outputs.clientId
    }
    exists: frontendExists
    viteBackendWsUrl: backendApp.outputs.SERVICE_BACKEND_URI
  }
}

// Deploy Aspire Dashboard
module aspireDashboard 'core/host/container-app-upsert.bicep' = {
  name: '${deployment().name}-dash'
  scope: resourceGroup
  params: {
    name: aspireDashboardName
    location: location
    tags: tags
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerName: 'aspire-dashboard'
    imageName: aspireDashboardImageName
    ingressEnabled: true
    external: true
    targetPort: aspireDashboardTargetPort
    additionalPorts: [
      {
        exposedPort: aspireDashboardAdditionalGrpcExposedPort
        targetPort: aspireDashboardAdditionalGrpcTargetPort
      }
      {
        exposedPort: aspireDashboardAdditionalHttpExposedPort
        targetPort: aspireDashboardAdditionalHttpTargetPort
      }
    ]
    env: [
      {
        name: 'ASPNETCORE_ENVIRONMENT'
        value: 'Production'
      }
      {
        name: 'ASPNETCORE_URLS'
        value: 'http://+:${aspireDashboardTargetPort}'
      }
      {
        name: 'DOTNET_DASHBOARD_UNSECURED_ALLOW_ANONYMOUS'
        value: 'true'
      }
    ]
  }
}

// Add an output for the Aspire Dashboard URL
output ASPIRE_DASHBOARD_URI string = aspireDashboard.outputs.uri

module storage 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: storageResourceGroup
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: storageResourceGroupLocation
    tags: tags
    sku: {
      name: 'Standard_LRS'
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 2
    }
    containers: [
      {
        name: storageContainerName
      }
    ]
  }
}

// Assign storage blob data contributor to the user for local runs
module storageRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-user'
  params: {
    principalId: principalId 
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' // built-in role definition id for storage blob data reader
    principalType: principalType
  }
}

// Assign storage blob data contributor to the identity
module storageContribRoleUser 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-contribrole-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    principalType: principalType
  }
}

// SYSTEM IDENTITIES
module azureOpenAiRoleApi 'core/security/role.bicep' = {
  scope: azureOpenAiResourceGroup
  name: 'openai-role-api'
  params: {
    principalId: identity.outputs.principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}

module storageRoleApi 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-role-api'
  params: {
    principalId: identity.outputs.principalId
    roleDefinitionId: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalType: 'ServicePrincipal'
  }
}

module storageContribRoleApi 'core/security/role.bicep' = {
  scope: storageResourceGroup
  name: 'storage-contribrole-api'
  params: {
    principalId: identity.outputs.principalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    principalType: 'ServicePrincipal'
  }
}

module dataScientistRole 'core/security/subscription-role.bicep' = {
  name: 'data-scientist-role'
  params: {
    principalId: backendApp.outputs.SERVICE_BACKEND_PRINCIPAL_ID
    roleDefinitionId: 'f6c7c914-8db3-469d-8ca1-694a8f32e121' // Azure ML Data Scientist
    principalType: 'ServicePrincipal'
  }
}

output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output APPLICATIONINSIGHTS_NAME string = monitoring.outputs.applicationInsightsName
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName
output AZURE_CONTAINER_REGISTRY_RESOURCE_GROUP string = containerApps.outputs.registryName
output AZURE_LOCATION string = location
output AZURE_FOUNDRY_HUB_NAME string = aiServices.outputs.name
output AZURE_FOUNDRY_HUB_ID string = aiServices.outputs.resourceId
output AZURE_FOUNDRY_PROJECT_NAME string = aiServices.outputs.aiProjectName
output AZURE_FOUNDRY_PROJECT_ID string = aiServices.outputs.aiProjectId
output AZURE_AI_SERVICE_CONNECTION_NAME string = aiServices.outputs.aiServiceConnectionName
output AZURE_AI_SERVICE_CONNECTION_ID string = aiServices.outputs.aiServiceConnectionId
output AZURE_COGNITIVE_SERVICES_NAME string = aiServices.outputs.cognitiveServicesAccountName
output AZURE_COGNITIVE_SERVICES_ID string = aiServices.outputs.cognitiveServicesAccountId
output AZURE_COGNITIVE_SERVICES_ENDPOINT string = aiServices.outputs.cognitiveServicesEndpoint
output AZURE_GPT4O_DEPLOYMENT_NAME string = aiServices.outputs.chatModelDeploymentName
output AZURE_EMBEDDING_MODEL_DEPLOYMENT_NAME string = aiServices.outputs.embeddingModelDeploymentName
output AZURE_GPT4O_MINI_MODEL_DEPLOYMENT_NAME string = aiServices.outputs.gpt4oMiniModelDeploymentName
output AZURE_REALTIME_MODEL_DEPLOYMENT_NAME string = aiServices.outputs.realtimeModelDeploymentName
output SERVICE_FRONTEND_IDENTITY_NAME string = frontendApp.outputs.SERVICE_FRONTEND_IDENTITY_NAME
output SERVICE_FRONTEND_NAME string = frontendApp.outputs.SERVICE_FRONTEND_NAME
output SERVICE_BACKEND_IDENTITY_NAME string = backendApp.outputs.SERVICE_BACKEND_IDENTITY_NAME
output SERVICE_BACKEND_NAME string = backendApp.outputs.SERVICE_BACKEND_NAME
output ASPIRE_DASHBOARD_FQDN string = aspireDashboard.outputs.defaultDomain

