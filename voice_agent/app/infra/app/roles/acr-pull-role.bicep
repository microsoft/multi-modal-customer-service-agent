@description('Name of the container registry')
param containerRegistryName string

@description('Principal ID of the identity that needs ACR pull access')
param principalId string

@description('Name of the app for description purposes')
param appName string

// Reference the container registry directly using the provided name
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

// Assign the AcrPull role to the identity
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, principalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalType: 'ServicePrincipal'
    description: 'Grant ${appName} app AcrPull access to the container registry'
  }
}

// Output the role assignment ID for reference
output roleAssignmentId string = acrPullRoleAssignment.id
