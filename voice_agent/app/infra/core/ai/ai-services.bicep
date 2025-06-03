@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('The AI Service Account SKU')
param accountSku string = 'S0'

@description('Name of the Foundry Hub')
param foundryHubName string = 'foundryHub'

@description('Name of the storage account used for the workspace.')
param storageAccountName string = replace(foundryHubName, '-', '')

@description('Resource ID of the Application Insights instance')
param applicationInsightsResourceId string

@description('Name of the Cognitive Services account')
param cognitiveServicesAccountName string = foundryHubName

@description('Name of the GPT-4o model deployment')
param gpt4oDeploymentName string = 'gpt-4o'

@description('Capacity for the GPT-4o model deployment')
param gpt4oCapacity int = 1

@description('Name of the embedding model deployment')
param embeddingModelDeploymentName string = 'text-embedding-ada-002'

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

//Create a dedicated container registry for AI services
module containerRegistry 'br/public:avm/res/container-registry/registry:0.1.1' = {
  name: 'ai-services-registry'
  params: {
    name: '${abbrs.containerRegistryRegistries}ai${resourceToken}'
    location: location
    tags: tags
    acrAdminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2019-04-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    supportsHttpsTrafficOnly: true
  }
  tags: tags
}

// Add Cognitive Services account of kind AIServices
resource cognitiveServicesAccount 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: cognitiveServicesAccountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: accountSku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
  }
}

// Create the AI Foundry Project
resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: cognitiveServicesAccount
  name: aiFoundryProjectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: aiFoundryProjectDisplayName
  }
  tags: tags
}

var contentUnderstandingEndpoint = 'https://${cognitiveServicesAccountName}.services.ai.azure.com/'

// Generate a unique token for resource naming
var resourceToken = uniqueString(subscription().id, resourceGroup().id, cognitiveServicesAccountName)

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
output gpt4oMiniModelVersion string = gpt4oMiniModelVersion
output realtimeModelDeploymentName string = realtimeModelDeploymentName
output containerRegistryName string = containerRegistry.outputs.name
