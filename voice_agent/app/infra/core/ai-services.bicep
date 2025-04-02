@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('Name of the Foundry Hub')
param foundryHubName string = 'foundryHub'

@description('Resource ID of the Application Insights instance')
param applicationInsightsResourceId string

//@description('Container Registry Resource Id')
//param containerRegistryResourceId string

@description('Name of the Cognitive Services account')
param cognitiveServicesAccountName string = foundryHubName

@description('Name of the GPT-4o model deployment')
param gpt4oDeploymentName string = 'gpt-4o'

@description('GPT-4o model name')
param gpt4oModelName string = 'gpt-4o'

@description('GPT-4o model version')
param gpt4oModelVersion string = '2024-05-13'

@description('Capacity for the GPT-4o model deployment')
param gpt4oCapacity int = 1

@description('Name of the embedding model deployment')
param embeddingModelDeploymentName string = 'text-embedding-ada-002'

@description('Embedding model version')
param embeddingModelVersion string = '2'

@description('Name of the GPT-4o mini deployment')
param gpt4oMiniModelDeploymentName string = 'gpt-4o-mini'

@description('Version for the GPT-4o mini model deployment')
param gpt4oMiniModelVersion string = '2024-07-18'

@description('Name of the Realtime Model deployment')
param realtimeModelDeploymentName string = 'gpt-4o-realtime-preview'

@description('Version for the realtime model deployment')
param realtimeModelVersion string = '2024-12-17'

@description('SKU for the Realtime model deployment')
param realTimeSkuName string = 'GlobalStandard'

@description('SKU for the OpenAI model deployment')
param openAiSkuName string = 'Standard'

@description('Format for the OpenAI model deployment')
param openAiModelFormat string = 'OpenAI'

@description('Name of the AI Foundry Project')
param aiFoundryProjectName string = '${foundryHubName}-project'

@description('Display name for the AI Foundry Project')
param aiFoundryProjectDisplayName string = 'Voice Agent Multi Modal Workshop'

@description('Abbreviations to use for resource naming')
param abbrs object

var keyVaultName = '${abbrs.keyVaultVaults}${resourceToken}-ai'

// Create a dedicated container registry for AI services
// module containerRegistry 'br/public:avm/res/container-registry/registry:0.1.1' = {
//   name: 'ai-services-registry'
//   params: {
//     name: '${abbrs.containerRegistryRegistries}ai${resourceToken}'
//     location: location
//     tags: tags
//     acrAdminUserEnabled: true
//     publicNetworkAccess: 'Enabled'
//   }
// }

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: foundryHubName
  location: location
  kind: 'hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'Azure AI Foundry Hub'
    friendlyName: 'AI Foundry Hub'
    publicNetworkAccess: 'Enabled'
    //containerRegistry: containerRegistryResourceId
    applicationInsights: applicationInsightsResourceId
    keyVault: keyVault.outputs.resourceId
  }
  tags: tags
}

// Create the AI Foundry Project
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: aiFoundryProjectName
  location: location
  kind: 'project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: 'AI Foundry Project for Video RAG'
    friendlyName: aiFoundryProjectDisplayName
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
  tags: tags
}

// Connect the Azure OpenAI endpoint to the AI Foundry Project
resource aiServiceConnection 'Microsoft.MachineLearningServices/workspaces/connections@2023-08-01-preview' = {
  parent: aiProject
  name: 'openai-connection'
  properties: {
    category: 'AzureOpenAI'
    target: cognitiveServicesAccount.properties.endpoint
    authType: 'ApiKey'
    isSharedToAll: false
    credentials: {
      key: cognitiveServicesAccount.listKeys().key1
    }
    metadata: {
      resourceName: cognitiveServicesAccount.name
      ApiType: 'ApiKey'
      ApiVersion: '2023-05-15'
      Kind: 'OpenAI'
      AuthType: 'ApiKey'
    }
  }
}

// Add Cognitive Services account of kind AIServices
resource cognitiveServicesAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: cognitiveServicesAccountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: cognitiveServicesAccountName
    networkAcls: {
      defaultAction: 'Allow'
    }
    publicNetworkAccess: 'Enabled'
  }
}

var contentUnderstandingEndpoint = 'https://${cognitiveServicesAccountName}.services.ai.azure.com/'

// User-assigned managed identity for the deployment script
resource deploymentScriptIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-deploymentscript-${resourceToken}'
  location: location
  tags: tags
}

// Create role assignment for the deployment script identity to manage Cognitive Services
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deploymentScriptIdentity.id, 'Contributor')
  scope: cognitiveServicesAccount
  properties: {
    principalId: deploymentScriptIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // Contributor role
    principalType: 'ServicePrincipal'
  }
}

// Generate a unique token for resource naming
var resourceToken = uniqueString(subscription().id, resourceGroup().id, cognitiveServicesAccountName)


resource chatModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: cognitiveServicesAccount
  name: gpt4oDeploymentName
  sku: {
    capacity: gpt4oCapacity
    name: openAiSkuName
  }
  properties: {
    model: {
      format: openAiModelFormat
      name: gpt4oModelName
      version: gpt4oModelVersion
    }
  }
}

resource embeddingModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: cognitiveServicesAccount
  name: embeddingModelDeploymentName
  sku: {
    capacity: gpt4oCapacity
    name: openAiSkuName
  }
  properties: {
    model: {
      format: openAiModelFormat
      name: embeddingModelDeploymentName
      version: embeddingModelVersion
    }
  }
  dependsOn: [
    chatModelDeployment
  ]
}

resource gpt4oMiniModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: cognitiveServicesAccount
  name: gpt4oMiniModelDeploymentName
  sku: {
    capacity: gpt4oCapacity
    name: openAiSkuName
  }
  properties: {
    model: {
      format: openAiModelFormat
      name: gpt4oMiniModelDeploymentName
      version: gpt4oMiniModelVersion
    }
  }
  dependsOn: [
    embeddingModelDeployment
  ]
}

resource realtimeModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: cognitiveServicesAccount
  name: realtimeModelDeploymentName
  sku: {
    capacity: gpt4oCapacity
    name: realTimeSkuName
  }
  properties: {
    model: {
      format: openAiModelFormat
      name: realtimeModelDeploymentName
      version: realtimeModelVersion
    }
  }
  dependsOn: [
    gpt4oMiniModelDeployment
  ]
}

module keyVault 'br/public:avm/res/key-vault/vault:0.6.1' = {
  name: keyVaultName
  params: {
    name: keyVaultName
    location: location
    tags: tags
    enableRbacAuthorization: true
  }
}

output cognitiveServicesAccountName string = cognitiveServicesAccount.name
output cognitiveServicesAccountId string = cognitiveServicesAccount.id
output cognitiveServicesEndpoint string = cognitiveServicesAccount.properties.endpoint
output contentUnderstandingEndpoint string = contentUnderstandingEndpoint
output chatModelDeploymentName string = gpt4oDeploymentName
output embeddingModelDeploymentName string = embeddingModelDeploymentName
output gpt4oMiniModelDeploymentName string = gpt4oMiniModelDeploymentName
output realtimeModelDeploymentName string = realtimeModelDeploymentName
output aiProjectName string = aiProject.name
output aiProjectId string = aiProject.id
output aiProjectPrincipalId string = aiProject.identity.principalId
output aiServiceConnectionName string = aiServiceConnection.name
output aiServiceConnectionId string = aiServiceConnection.id
output resourceId string = aiHub.id
output name string = aiHub.name
output principalId string = aiHub.identity.principalId
// output containerRegistryName string = containerRegistry.outputs.name
