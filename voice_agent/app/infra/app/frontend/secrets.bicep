@description('The name of the Key Vault to store secrets')
param keyVaultName string

@description('The name of the Storage Account')
param storageAccountName string

@description('The name of the blob container')
param blobContainerName string

@description('The URL for the backend WebSocket connection')
param viteBackendWsUrl string = ''

@description('API version for Storage operations')
param storageApiVersion string = '2022-09-01'

// Storage Account secrets
resource storageAccountNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/index-file-api-storage-account-name'
  properties: {
    value: storageAccountName
  }
}

resource storageAccountApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/index-file-api-storage-account-key'
  properties: {
    value: listKeys(resourceId('Microsoft.Storage/storageAccounts', storageAccountName), storageApiVersion).keys[0].value
  }
}

resource containerNameSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = {
  name: '${keyVaultName}/index-file-api-container-name'
  properties: {
    value: blobContainerName
  }
}

resource viteBackendWsUrlSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(viteBackendWsUrl)) {
  name: '${keyVaultName}/index-file-api-vite-backend-ws-url'
  properties: {
    value: viteBackendWsUrl
  }
}

// Output secret URIs for reference by container apps
output storageAccountNameSecretUri string = storageAccountNameSecret.properties.secretUri
output storageAccountKeySecretUri string = storageAccountApiKeySecret.properties.secretUri
output containerNameSecretUri string = containerNameSecret.properties.secretUri
output viteBackendWsUrlSecretUri string = viteBackendWsUrlSecret.properties.secretUri
