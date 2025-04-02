@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('Application Insights resource ID for monitoring')
param applicationInsightsResourceId string

@description('Resource ID of the Container App Environment')
param containerAppsEnvironmentResourceId string

@description('Storage account name')
param storageAccountName string

@description('Blob container name')
param blobContainerName string

@description('Cognitive Services account name')
param cognitiveServicesAccountName string = ''

@description('OpenAI deployment name')
param openAiChatDeploymentName string = ''

@description('OpenAI embedding deployment name')
param openAiEmbeddingDeploymentName string = ''

@description('OpenAI 4o mini deployment name')
param openAi4oMiniDeploymentName string = ''

@description('OpenAI Realtime deployment name')
param openAiRealtimeDeploymentName string = ''

@description('Resource token for unique resource naming')
param resourceToken string

@description('Abbreviations to use for resource naming')
param abbrs object

@description('Name of the app')
param name string = 'backend'

var keyVaultName = '${abbrs.keyVaultVaults}${resourceToken}-backend'

// Create managed identities for the container apps
module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'backendidentity'
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}backend-${resourceToken}'
    location: location
  }
}

// Create container registry for this app with direct role assignment
module containerRegistry 'br/public:avm/res/container-registry/registry:0.1.1' = {
  name: 'backend-registry'
  params: {
    name: '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: tags
    acrAdminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    roleAssignments: [
      {
        principalId: identity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
      }
    ]
  }
}

// Deploy Key Vault without inline secrets
module keyVault 'br/public:avm/res/key-vault/vault:0.6.1' = {
  name: keyVaultName
  params: {
    name: keyVaultName
    location: location
    tags: tags
    enableRbacAuthorization: true
  }
}

// Create secrets for backend in a dedicated module
module backendSecrets 'secrets.bicep' = {
  name: 'backendSecrets'
  params: {
    keyVaultName: keyVaultName
    storageAccountName: storageAccountName
    blobContainerName: blobContainerName
    cognitiveServicesAccountName: cognitiveServicesAccountName
    openAiChatDeploymentName: openAiChatDeploymentName
    openAi4oMiniDeploymentName: openAi4oMiniDeploymentName
    openAiRealtimeDeploymentName: openAiRealtimeDeploymentName
    openAiEmbeddingDeploymentName: openAiEmbeddingDeploymentName
  }
  dependsOn: [
    keyVault
  ]
}

// Grant Storage Blob Data Contributor role to the identity
module storageBlobContributorRole '../roles/storage-blob-contributor-role.bicep' = if (!empty(storageAccountName)) {
  name: '${name}-storage-blob-contributor-role'
  params: {
    storageAccountName: storageAccountName
    containerName: blobContainerName
    principalId: identity.outputs.principalId
    appName: name
  }
}

// Grant Key Vault Secret User role to the identity
module keyVaultSecretUserRole '../roles/key-vault-secret-user-role.bicep' = {
  name: '${name}-key-vault-secret-user-role'
  params: {
    keyVaultName: keyVaultName
    principalId: identity.outputs.principalId
    appName: name
  }
  dependsOn:[
    keyVault
  ]
}

// Deploy Summarize Video Content Container App
module backend '../container-app.bicep' = {
  name: 'backendContainerApp'
  params: {
    name: name
    location: location
    tags: tags
    applicationInsightsResourceId: applicationInsightsResourceId
    containerAppsEnvironmentResourceId: containerAppsEnvironmentResourceId
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    identityResourceId: identity.outputs.resourceId
    identityClientId: identity.outputs.clientId
    secrets: {
      secrets: [
        {
          name: 'azure-openai-endpoint'
          keyVaultUrl: backendSecrets.outputs.openAiEndpointSecretUri
        }
        {
          name: 'azure-openai-key'
          keyVaultUrl: backendSecrets.outputs.openAiKeySecretUri
        }
        {
          name: 'azure-openai-api-version'
          keyVaultUrl: backendSecrets.outputs.openAiApiVersionSecretUri
        }
        {
          name: 'azure-openai-chat-deployment-name'
          keyVaultUrl: backendSecrets.outputs.openAiChatDeploymentNameSecretUri
        }
        {
          name: 'azure-openai-embedding-deployment-name'
          keyVaultUrl: backendSecrets.outputs.openAiEmbeddingDeploymentNameSecretUri
        }
        {
          name: 'azure-openai-4o-mini-deployment-name'
          keyVaultUrl: backendSecrets.outputs.openAi4oMiniDeploymentNameSecretUri
        }
        {
          name: 'azure-openai-realtime-deployment-name'
          keyVaultUrl: backendSecrets.outputs.openAiRealtimeDeploymentNameSecretUri
        }
        {
          name: 'azure-openai-realtime-endpoint'
          keyVaultUrl: backendSecrets.outputs.openAiRealtimeDeploymentNameSecretUri
        }
        {
          name: 'azure-openai-realtime-key'
          keyVaultUrl: backendSecrets.outputs.openAiRealtimeDeploymentNameSecretUri
        }
        {
          name: 'storage-account-name'
          keyVaultUrl: backendSecrets.outputs.storageAccountNameSecretUri
        }
        {
          name: 'storage-container-name'
          keyVaultUrl: backendSecrets.outputs.containerNameSecretUri
        }
        {
          name: 'storage-account-api-key'
          keyVaultUrl: backendSecrets.outputs.storageAccountKeySecretUri
        }
      ]
    }
    envVars: [
      { name: 'AZURE_OPENAI_RT_ENDPOINT', secretRef: 'azure-openai-realtime-endpoint' }
      { name: 'AZURE_OPENAI_RT_API_KEY', secretRef: 'azure-openai-key' }
      { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-key' }
      { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', secretRef: 'azure-openai-chat-deployment-name' }
      { name: 'AZURE_OPENAI_4O_MINI_DEPLOYMENT', secretRef: 'azure-openai-4o-mini-deployment-name' }
      { name: 'AZURE_OPENAI_EMB_DEPLOYMENT', secretRef: 'azure-openai-embedding-deployment-name'}
      { name: 'AZURE_OPENAI_API_VERSION', secretRef: 'azure-openai-api-version' }
      { name: 'AZURE_OPENAI_RT_DEPLOYMENT', secretRef: 'azure-openai-realtime-deployment-name' }
      { name: 'AZURE_OPENAI_ENDPOINT', secretRef: 'azure-openai-endpoint' }
      { name: 'STORAGE_ACCOUNT_NAME', secretRef: 'storage-account-name' }
      { name: 'STORAGE_CONTAINER_NAME', secretRef: 'storage-container-name' }
      { name: 'STORAGE_ACCOUNT_API_KEY', secretRef: 'storage-account-api-key' }
    ]
    imageName: 'backend'
  }
  dependsOn: [
    keyVaultSecretUserRole
    storageBlobContributorRole
  ]
}

output resourceId string = backend.outputs.resourceId
output identityPrincipalId string = identity.outputs.principalId
output identityResourceId string = identity.outputs.resourceId
output identityClientId string = identity.outputs.clientId
output containerRegistryName string = containerRegistry.outputs.name
output backendContainerAppUri string = backend.outputs.containerAppUri
