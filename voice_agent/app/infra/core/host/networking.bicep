@description('The Azure region for the resources.')
param location string

@description('Tags to apply to the resources.')
param tags object = {}

@description('Name for the virtual network.')
param vnetName string

@description('Address prefix for the virtual network.')
param vnetAddressPrefix string

@description('Name for the infrastructure subnet.')
param infrastructureSubnetName string = 'infrastructure-subnet'

@description('Address prefix for the infrastructure subnet.')
param infrastructureSubnetPrefix string

@description('Name for the Container Apps subnet.')
param containerAppsSubnetName string = 'containerapps-subnet'

@description('Address prefix for the Container Apps subnet.')
param containerAppsSubnetPrefix string

// Create the virtual network
resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-04-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: infrastructureSubnetName
        properties: {
          addressPrefix: infrastructureSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: containerAppsSubnetName
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
    ]
  }
}

// Output the subnet details
output vnetId string = virtualNetwork.id
output vnetName string = virtualNetwork.name
output infrastructureSubnetId string = virtualNetwork.properties.subnets[0].id
output containerAppsSubnetId string = virtualNetwork.properties.subnets[1].id
output infrastructureSubnetName string = infrastructureSubnetName
output containerAppsSubnetName string = containerAppsSubnetName
