// /infra/main.bicep

@minLength(1)
@maxLength(64)
@description('Name of the workload which is used to generate a short unique hash used in all resources.')
param workloadName string

@description('Primary location for all resources.')
@allowed([
  'westus'
])
param location string = 'westus'

@description('Resource for static web app')
@allowed([
  'westus2'
  'eastus2'
  'southcentralus'
  'eastasia'
])
param staticWebAppLocation string = 'westus2'

@description('Tags to add to the resources.')
param tags object = {}

@description('Public network access')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Authentication mode: accessKey or rbac')
@allowed(['accessKey', 'rbac'])
param authMode string = 'rbac'

@description('GPT-4 model deployment capacity')
@minValue(1)
@maxValue(100)
param modelCapacity int = 10

@description('Model version')
param modelVersion string = '2024-05-13'

// Generate unique suffix
var resourceSuffix = uniqueString(resourceGroup().id, workloadName)

// Resource names
var storageAccountName = 'st${resourceSuffix}'
var searchServiceName = 'srch-${resourceSuffix}'
var aiServicesName = 'ai-${resourceSuffix}'
var functionAppName = 'func-${resourceSuffix}'
var appServicePlanName = 'asp-${resourceSuffix}'
var staticWebAppName = 'swa-${resourceSuffix}'
var appInsightsName = 'appi-${resourceSuffix}'
var logAnalyticsName = 'log-${resourceSuffix}'

// Storage for files and configuration
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    defaultToOAuthAuthentication: true
    allowSharedKeyAccess: true
    networkAcls: {
      defaultAction: publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny'
      bypass: 'AzureServices,Logging,Metrics'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

// Containers
resource schemasContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'schemas'
}

resource filesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'files'
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Azure AI Search
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'free'
    publicNetworkAccess: publicNetworkAccess == 'Enabled' ? 'enabled' : 'disabled'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

// Azure AI Services
resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: aiServicesName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    networkAcls: {
      defaultAction: publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny'
    }
    publicNetworkAccess: publicNetworkAccess
    apiProperties: {
      statisticsEnabled: false
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// GPT-4 Model Deployment
resource gpt4Deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: aiServices
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: modelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Default'
  }
}

// Application Insights
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Function App hosting
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {}
}

// Role Assignments with Function App principal ID variable
var functionAppPrincipalId = reference(functionAppName, '2022-09-01', 'full').identity.principalId

// Function App role assignments
resource functionStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionAppName, blobDataContributor.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: blobDataContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionSearchAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionAppName, searchContributor.id)
  scope: searchService
  properties: {
    roleDefinitionId: searchContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAiAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionAppName, cognitiveServicesUser.id)
  scope: aiServices
  properties: {
    roleDefinitionId: cognitiveServicesUser.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionOpenAIAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionAppName, openAIContributor.id)
  scope: aiServices
  properties: {
    roleDefinitionId: openAIContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionFileShareAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionAppName, fileShareContributor.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: fileShareContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    clientCertEnabled: true
    siteConfig: {
      pythonVersion: '3.10'
      cors: {
        allowedOrigins: [
          'https://${staticWebAppName}.azurestaticapps.net'
          'http://localhost:3000'
        ]
      }
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'SEARCH_ENDPOINT'
          value: 'https://${searchService.name}.search.windows.net'
        }
        {
          name: 'SEARCH_ADMIN_KEY'
          value: searchService.listAdminKeys().primaryKey
        }
        {
          name: 'SEARCH_INDEX_NAME'
          value: 'artifact-index'
        }
        {
          name: 'AI_ENDPOINT'
          value: aiServices.properties.endpoint
        }
        {
          name: 'AI_KEY'
          value: aiServices.listKeys().key1
        }
        {
          name: 'GPT_DEPLOYMENT_NAME'
          value: gpt4Deployment.name
        }
      ]
    }
  }
}

// Static Web App
resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: staticWebAppName
  location: staticWebAppLocation
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    buildProperties: {
      skipGithubActionWorkflowGeneration: true
    }
    allowConfigFileUpdates: true
    enterpriseGradeCdnStatus: 'Disabled'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Link function app to static web app
resource staticWebAppBackend 'Microsoft.Web/staticSites/linkedBackends@2022-09-01' = {
  parent: staticWebApp
  name: 'backend'
  properties: {
    backendResourceId: functionApp.id
    region: location
  }
}

// Role Assignments
resource searchContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
}

resource blobDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
}

resource cognitiveServicesUser 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: 'a97b65f3-24c7-4388-baec-2e87135dc908'
}

resource openAIContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: 'a001fd3d-188f-4b5d-821b-7da978bf7442'
}

resource fileShareContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: '0c867c2a-1d8c-454a-a3db-ab2ea1bdc8bb'
}

output functionAppName string = functionApp.name
output storageAccountName string = storageAccount.name
output searchServiceName string = searchService.name
output aiServicesName string = aiServices.name
output staticWebAppName string = staticWebApp.name
output staticWebAppUri string = staticWebApp.properties.defaultHostname
output functionAppUri string = functionApp.properties.defaultHostName
