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
        name: containerAppsSubnetName
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: infrastructureSubnetName
        properties: {
          addressPrefix: infrastructureSubnetPrefix
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

// Add a Network Security Group (NSG) rule to allow inbound 443 traffic on the container apps subnet
resource containerAppsSubnetNsg 'Microsoft.Network/networkSecurityGroups@2023-04-01' = {
  name: '${containerAppsSubnetName}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-Inbound-443'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'Allow-Inbound-Intra-VNet-18889'
        properties: {
          priority: 200
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '18889'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
      {
        name: 'Allow-Inbound-Intra-VNet-18890'
        properties: {
          priority: 201
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '18890'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
      {
        name: 'Allow-Outbound-443'
        properties: {
          priority: 100
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'Allow-Outbound-Intra-VNet-18889'
        properties: {
          priority: 200
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '18889'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
      {
        name: 'Allow-Outbound-Intra-VNet-18890'
        properties: {
          priority: 201
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '18890'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
    ]
  }
}

// Associate the NSG with the container apps subnet
resource containerAppsSubnetNsgAssociation 'Microsoft.Network/virtualNetworks/subnets@2023-04-01' = {
  parent: virtualNetwork
  name: containerAppsSubnetName
  properties: {
    addressPrefix: containerAppsSubnetPrefix
    networkSecurityGroup: {
      id: containerAppsSubnetNsg.id
    }
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
  }
}

// Output the subnet details
output vnetId string = virtualNetwork.id
output vnetName string = virtualNetwork.name
output infrastructureSubnetId string = virtualNetwork.properties.subnets[0].id
output containerAppsSubnetId string = virtualNetwork.properties.subnets[1].id
output infrastructureSubnetName string = infrastructureSubnetName
output containerAppsSubnetName string = containerAppsSubnetName
