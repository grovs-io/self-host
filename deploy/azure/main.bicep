targetScope = 'resourceGroup'

@description('Azure region for the VM, disk and network.')
param location string = resourceGroup().location

@description('App base domain, for example grovs.example.com, without https:// or a path.')
@minLength(4)
param appDomain string

@description('Email address for the first Grovs administrator.')
@minLength(5)
param adminEmail string

@description('Your SSH public key (the contents of your .pub file). Never enter a private key.')
@minLength(40)
param sshPublicKey string

@description('Linux administrator username, used only for SSH access.')
param adminUsername string = 'grovsadmin'

@description('Your public IPv4 address with /32, for example 203.0.113.10/32. Only this source may SSH.')
@minLength(9)
@maxLength(18)
param sshSourceCidr string

@description('Published release shared by the backend and dashboard images.')
param grovsVersion string = '2.3.1'

@description('Reviewed self-host Git commit containing the Compose stack. Keep pinned for repeatable installs.')
param stackRef string = 'd9f291fb7a943adc8b712696342180ea63438cfd'

@description('VM size; the default has 4 vCPUs and 16 GiB RAM. Availability depends on your region and quota.')
@allowed([
  'Standard_D4s_v5'
  'Standard_D8s_v5'
  'Standard_D4s_v6'
  'Standard_D8s_v6'
])
param vmSize string = 'Standard_D4s_v5'

@description('Persistent OS disk in GiB, including database and upload volumes. Detached when the VM alone is deleted.')
@minValue(80)
@maxValue(1024)
param diskSizeGb int = 128

var prefix = 'grovs-${uniqueString(resourceGroup().id)}'
// Base64 prevents parameter text from becoming executable shell syntax.
// No generated passwords or encryption keys are stored in Azure parameters.
var startupTemplate = '''#!/usr/bin/env bash
set -euo pipefail
export GROVS_DOMAIN="$(printf %s '__DOMAIN__' | base64 --decode)"
export GROVS_ADMIN_EMAIL="$(printf %s '__EMAIL__' | base64 --decode)"
export GROVS_VERSION="$(printf %s '__VERSION__' | base64 --decode)"
export GROVS_STACK_REF="$(printf %s '__REF__' | base64 --decode)"
'''
var startupHeader = replace(replace(replace(replace(startupTemplate,
    '__DOMAIN__', base64(appDomain)), '__EMAIL__', base64(adminEmail)),
    '__VERSION__', base64(grovsVersion)), '__REF__', base64(stackRef))
var startup = '${startupHeader}\n${loadTextContent('../vm/bootstrap.sh')}'

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${prefix}-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'http-https'
        properties: {
          priority: 100
          access: 'Allow'
          direction: 'Inbound'
          protocol: 'Tcp'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRanges: ['80', '443']
        }
      }
      {
        name: 'ssh-from-operator'
        properties: {
          priority: 110
          access: 'Allow'
          direction: 'Inbound'
          protocol: 'Tcp'
          sourceAddressPrefix: sshSourceCidr
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }
    ]
  }
}

resource network 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${prefix}-vnet'
  location: location
  properties: {
    addressSpace: { addressPrefixes: ['10.42.0.0/16'] }
    subnets: [
      {
        name: 'grovs'
        properties: {
          addressPrefix: '10.42.0.0/24'
          networkSecurityGroup: { id: nsg.id }
        }
      }
    ]
  }
}

resource publicIp 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: '${prefix}-ip'
  location: location
  sku: { name: 'Standard' }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

resource nic 'Microsoft.Network/networkInterfaces@2024-05-01' = {
  name: '${prefix}-nic'
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'primary'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: { id: network.properties.subnets[0].id }
          publicIPAddress: { id: publicIp.id }
        }
      }
    ]
  }
}

resource vm 'Microsoft.Compute/virtualMachines@2024-07-01' = {
  name: prefix
  location: location
  properties: {
    hardwareProfile: { vmSize: vmSize }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: 'latest'
      }
      osDisk: {
        name: '${prefix}-data'
        createOption: 'FromImage'
        deleteOption: 'Detach'
        diskSizeGB: diskSizeGb
        managedDisk: { storageAccountType: 'Premium_LRS' }
      }
    }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: { secureBootEnabled: true, vTpmEnabled: true }
    }
    osProfile: {
      computerName: prefix
      adminUsername: adminUsername
      customData: base64(startup)
      linuxConfiguration: {
        disablePasswordAuthentication: true
        provisionVMAgent: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: sshPublicKey
            }
          ]
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        { id: nic.id, properties: { primary: true } }
      ]
    }
  }
}

output ipAddress string = publicIp.properties.ipAddress
output dashboard string = 'https://dashboard.${appDomain}'
output vmName string = vm.name
output sshCommand string = 'ssh ${adminUsername}@${publicIp.properties.ipAddress}'
