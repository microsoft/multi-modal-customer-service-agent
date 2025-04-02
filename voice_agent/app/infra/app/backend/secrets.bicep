@description('The name of the Key Vault to store secrets')
param keyVaultName string

@description('The name of the Storage Account')
param storageAccountName string

@description('The name of the blob container')
param blobContainerName string

@description('The name of the Cognitive Services account')
param cognitiveServicesAccountName string = ''

@description('The name of the OpenAI chat deployment')
param openAiChatDeploymentName string = ''

@description('The name of the OpenAI text embedding deployment')
param openAiEmbeddingDeploymentName string = ''

@description('The name of the OpenAI 4o Mini deployment')
param openAi4oMiniDeploymentName string = ''

@description('The name of the OpenAI Realtime deployment')
param openAiRealtimeDeploymentName string = ''

@description('API version for Storage operations')
param storageApiVersion string = '2022-09-01'

@description('API version for Cognitive Services operations')
param cognitiveServicesApiVersion string = '2023-05-01'

// Storage Account secrets
resource storageAccountNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/backend-storage-account-name'
  properties: {
    value: storageAccountName
  }
}

resource storageAccountApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/backend-storage-account-key'
  properties: {
    value: listKeys(resourceId('Microsoft.Storage/storageAccounts', storageAccountName), storageApiVersion).keys[0].value
  }
}

resource containerNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/backend-container-name'
  properties: {
    value: blobContainerName
  }
}

// OpenAI secrets
resource openAiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(cognitiveServicesAccountName)) {
  name: '${keyVaultName}/backend-open-ai-endpoint'
  properties: {
    value: reference(resourceId('Microsoft.CognitiveServices/accounts', cognitiveServicesAccountName), cognitiveServicesApiVersion).endpoint
  }
}

resource openAiKeySecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(cognitiveServicesAccountName)) {
  name: '${keyVaultName}/backend-open-ai-key'
  properties: {
    value: listKeys(resourceId('Microsoft.CognitiveServices/accounts', cognitiveServicesAccountName), cognitiveServicesApiVersion).key1
  }
}

resource openAiChatDeploymentNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openAiChatDeploymentName)) {
  name: '${keyVaultName}/backend-open-ai-chat-deployment-name'
  properties: {
    value: openAiChatDeploymentName
  }
}

resource openAiEmbeddingDeploymentNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openAiEmbeddingDeploymentName)) {
  name: '${keyVaultName}/backend-open-ai-embedding-deployment-name'
  properties: {
    value: openAiChatDeploymentName
  }
}

resource openAi4oMiniDeploymentNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openAi4oMiniDeploymentName)) {
  name: '${keyVaultName}/backend-open-ai-deployment-name'
  properties: {
    value: openAi4oMiniDeploymentName
  }
}

resource openAiRealtimeDeploymentNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openAiRealtimeDeploymentName)) {
  name: '${keyVaultName}/backend-open-ai-realtime-deployment-name'
  properties: {
    value: openAiRealtimeDeploymentName
  }
}


resource openAiApiVersionSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/backend-azure-openai-api-version'
  properties: {
    value: '2023-05-15'
  }
}

// Output secret URIs for reference by container apps
output storageAccountNameSecretUri string = storageAccountNameSecret.properties.secretUri
output storageAccountKeySecretUri string = storageAccountApiKeySecret.properties.secretUri
output containerNameSecretUri string = containerNameSecret.properties.secretUri
output openAiEndpointSecretUri string = !empty(cognitiveServicesAccountName) ? openAiEndpointSecret.properties.secretUri : ''
output openAiKeySecretUri string = !empty(cognitiveServicesAccountName) ? openAiKeySecret.properties.secretUri : ''
output openAiChatDeploymentNameSecretUri string = !empty(openAiChatDeploymentName) ? openAiChatDeploymentNameSecret.properties.secretUri : ''
output openAiEmbeddingDeploymentNameSecretUri string = !empty(openAiEmbeddingDeploymentName) ? openAiEmbeddingDeploymentNameSecret.properties.secretUri : ''
output openAi4oMiniDeploymentNameSecretUri string = !empty(openAi4oMiniDeploymentName) ? openAi4oMiniDeploymentNameSecret.properties.secretUri : ''
output openAiRealtimeDeploymentNameSecretUri string = !empty(openAiRealtimeDeploymentName) ? openAiRealtimeDeploymentNameSecret.properties.secretUri : ''
output openAiApiVersionSecretUri string = openAiApiVersionSecret.properties.secretUri
