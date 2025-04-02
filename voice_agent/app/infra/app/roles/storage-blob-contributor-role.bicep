@description('Name of the storage account')
param storageAccountName string

@description('Name of the blob container')
param containerName string = 'videos'

@description('Principal ID of the identity that needs Storage Blob Data Contributor access')
param principalId string

@description('Name of the app for description purposes')
param appName string

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' existing = {
  name: '${storageAccountName}/default/${containerName}'
}

// Assign the Storage Blob Data Contributor role to the identity
resource blobContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(blobContainer.id, principalId, 'BlobContributor')
  scope: blobContainer
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
    description: 'Grant ${appName} app Storage Blob Data Contributor access'
  }
}

// Output the role assignment ID for reference
output roleAssignmentId string = blobContributorRoleAssignment.id
