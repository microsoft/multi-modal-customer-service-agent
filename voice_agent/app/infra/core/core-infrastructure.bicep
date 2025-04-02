@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('Name of the blob container to create in the storage account')
param blobContainerName string = 'videos'

var abbrs = loadJsonContent('../abbreviations.json')
var resourceToken = uniqueString(subscription().id, resourceGroup().id, location)

var storageAccountName = '${abbrs.storageStorageAccounts}${resourceToken}'

// Monitor application with Azure Monitor
module monitoring 'br/public:avm/ptn/azd/monitoring:0.1.0' = {
  name: 'monitoring'
  params: {
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: '${abbrs.portalDashboards}${resourceToken}'
    location: location
    tags: tags
  }
}

// Container apps environment
module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.4.5' = {
  name: 'container-apps-environment'
  params: {
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    zoneRedundant: false
  }
}

// Deploy Storage Account
module storageAccount 'br/public:avm/res/storage/storage-account:0.6.0' = {
  name: 'storage'  // Changed from storageAccountName to 'storage' to match proper module naming
  params: {
    name: storageAccountName
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    publicNetworkAccess: 'Enabled'
    allowBlobPublicAccess: false
    defaultToOAuthAuthentication: true
  }
}

// Create Blob Container in Storage Account with proper parent/child relationship
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccountName}/default/${blobContainerName}'
  properties: {
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccount
  ]
}

output logAnalyticsWorkspaceResourceId string = monitoring.outputs.logAnalyticsWorkspaceResourceId
output applicationInsightsResourceId string = monitoring.outputs.applicationInsightsResourceId
output containerAppsEnvironmentResourceId string = containerAppsEnvironment.outputs.resourceId
output storageAccountResourceId string = storageAccount.outputs.resourceId
output storageAccountName string = storageAccount.outputs.name
output blobContainerName string = blobContainerName
output blobEndpoint string = storageAccount.outputs.primaryBlobEndpoint
