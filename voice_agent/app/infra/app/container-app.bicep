@description('The name of the container app')
param name string

@description('The location used for all deployed resources')
param location string = resourceGroup().location

@description('Tags that will be applied to all resources')
param tags object = {}

@description('Application Insights resource ID for monitoring')
param applicationInsightsResourceId string

@description('Container Apps Environment Resource ID')
param containerAppsEnvironmentResourceId string

@description('Container Registry Login Server')
param containerRegistryLoginServer string

@description('Identity resource ID')
param identityResourceId string

@description('Identity client ID')
param identityClientId string

@description('App secrets')
@secure()
param secrets object

@description('Environment variables')
param envVars array

@description('Name to fetch the latest image')
param imageName string

// Get the Application Insights resource using its ID
resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: split(applicationInsightsResourceId, '/')[8] // Extract name from resource ID
  scope: resourceGroup(split(applicationInsightsResourceId, '/')[2], split(applicationInsightsResourceId, '/')[4]) // Extract subscription and resource group
}

// Fetch latest image
module fetchLatestImage 'fetch-container-image.bicep' = {
  name: '${name}-fetch-image'
  params: {
    exists: false
    name: imageName
  }
}

// Add managed identity to the secret records
var secretsWithIdentity = [for secret in secrets.secrets: {
  name: secret.name
  keyVaultUrl: secret.keyVaultUrl
  identity: identityResourceId
}]

// Deploy container app
module app 'br/public:avm/res/app/container-app:0.8.0' = {
  name: name
  params: {
    name: imageName
    ingressTargetPort: 80
    scaleMinReplicas: 1
    scaleMaxReplicas: 10
    secrets: {
      secureList: secretsWithIdentity
    }
    containers: [
      {
        image: fetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        name: 'main'
        resources: {
          cpu: json('0.5')
          memory: '1.0Gi'
        }
        env: union([
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: appInsights.properties.ConnectionString
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: identityClientId
          }
          {
            name: 'PORT'
            value: '80'
          }
        ],
        envVars
        )
      }
    ]
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [identityResourceId]
    }
    registries: [
      {
        server: containerRegistryLoginServer
        identity: identityResourceId
      }
    ]
    environmentResourceId: containerAppsEnvironmentResourceId
    location: location
    tags: union(tags, { 'azd-service-name': imageName })
  }
}

output resourceId string = app.outputs.resourceId
output containerAppUri string = app.outputs.fqdn
