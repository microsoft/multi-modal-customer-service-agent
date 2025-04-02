@description('Key Vault name')
param keyVaultName string

@description('Principal ID of the identity that needs Key Vault Secret User access')
param principalId string

@description('Name of the app for description purposes')
param appName string

// Reference the Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' existing = {
  name: keyVaultName
}

// Assign the Key Vault Secrets User role to the identity
resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalId, 'SecretsUser')
  scope: keyVault
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalType: 'ServicePrincipal'
    description: 'Grant ${appName} app read access to Key Vault secrets'
  }
}

// Output the role assignment ID for reference
output roleAssignmentId string = keyVaultSecretsUserRoleAssignment.id
