@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('API version for Azure OpenAI API')
param azureOpenaiApiVersion string = '2023-05-15'

@description('Name of the frontend container app')
param frontendContainerAppName string = 'frontend'

@description('Name of the backend container app')
param backendContainerAppName string = 'backend'

@description('Name of the frontend image')
param frontendImageName string = ''

@description('Name of the backend image')
param backendImageName string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = uniqueString(subscription().id, resourceGroup().id, location)

// Deploy core infrastructure (monitoring, container registry, container apps environment, key vault)
module coreInfra './core/core-infrastructure.bicep' = {
  name: 'core-infrastructure'
  params: {
    location: location
    tags: tags
  }
}

// Deploy the Foundry Hub from the module
module aiServices './core/ai-services.bicep' = {
  name: 'ai-services'
  params: {
    location: location
    tags: tags
    foundryHubName: '${abbrs.machineLearningServicesWorkspaces}${resourceToken}'
    applicationInsightsResourceId: coreInfra.outputs.applicationInsightsResourceId
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

// Create a user assigned identity
// module identity './core/security/user-assigned-identity.bicep' = {
//   name: 'identity'
//   scope: resourceGroup()
//   params: {
//     name: 'sk-app-identity'
//   }
// }


// Deploy individual container apps
module backendApp './app/backend/app.bicep' = {
  name: 'backend-app'
  params: {
    location: location
    tags: tags
    applicationInsightsResourceId: coreInfra.outputs.applicationInsightsResourceId
    containerAppsEnvironmentResourceId: coreInfra.outputs.containerAppsEnvironmentResourceId
    storageAccountName: coreInfra.outputs.storageAccountName
    blobContainerName: coreInfra.outputs.blobContainerName
    cognitiveServicesAccountName: aiServices.outputs.cognitiveServicesAccountName
    openAiChatDeploymentName: aiServices.outputs.chatModelDeploymentName
    openAi4oMiniDeploymentName: aiServices.outputs.gpt4oMiniModelDeploymentName
    openAiRealtimeDeploymentName: aiServices.outputs.realtimeModelDeploymentName
    openAiEmbeddingDeploymentName: aiServices.outputs.embeddingModelDeploymentName
    abbrs: abbrs
    resourceToken: resourceToken
  }
}

// module frontendApp './app-modules/frontend/app.bicep' = {
//   name: 'frontend-app'
//   params: {
//     name: !empty(frontendContainerAppName) ? frontendContainerAppName : '${abbrs.appContainerApps}web-${resourceToken}'

//     applicationInsightsResourceId: coreInfra.outputs.applicationInsightsResourceId
//     containerAppsEnvironmentResourceId: coreInfra.outputs.containerAppsEnvironmentResourceId
//     containerRegistryName: aiServices.outputs.containerRegistryName
//     storageAccountNameParam: coreInfra.outputs.storageAccountName
//     blobContainerNameParam: coreInfra.outputs.blobContainerName
//     abbrs: abbrs
//     resourceToken: resourceToken
//     viteBackendWsUrl: backendApp.outputs.backendContainerAppUri

//     location: location
//     tags: tags
//     imageName: frontendImageName
//     identityName: identity.outputs.name
//     applicationInsightsName: monitoring.outputs.applicationInsightsName
//     containerAppsEnvironmentName: containerApps.outputs.environmentName
//     containerRegistryName: containerApps.outputs.registryName
//     userAssignedManagedIdentity: {
//       resourceId: identity.outputs.resourceId
//       clientId: identity.outputs.clientId
//     }
//     exists: webAppExists
//     apiEndpoint: '${api.outputs.SERVICE_API_URI}/chat'
//     serviceBinds: []
//   }
// }

// Add new outputs for Content Understanding
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
// output AZURE_STORAGE_ACCOUNT_NAME string = coreInfra.outputs.storageAccountName
// output AZURE_STORAGE_CONTAINER_NAME string = coreInfra.outputs.blobContainerName
