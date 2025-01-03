// Core Parameters
@minLength(1)
@maxLength(64)
@description('Name of the workload which is used to generate a short unique hash used in all resources.')
param workloadName string

// Region Parameters
@description('Primary region for AI and core services')
@allowed(['eastus'])
param primaryRegion string = 'eastus'

@description('Region for web hosting and static content')
@allowed(['westus2'])
param webHostingRegion string = 'westus2'

@description('Region for content understanding services')
@allowed(['australiaeast'])
param contentUnderstandingRegion string = 'australiaeast'

@description('Region for content understanding services')
@allowed(['westus2'])
param functionHostingRegion string = 'westus2'

// Network and Security Parameters
@description('Public network access configuration')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

// AI Service Parameters
@description('GPT-4 model deployment capacity')
@minValue(1)
@maxValue(100)
param gpt4ModelCapacity int = 10

@description('GPT-4 model version')
param gpt4ModelVersion string = '2024-05-13'

@description('AI Service Account type')
@allowed(['OpenAI', 'AIServices'])
param aiServiceType string = 'AIServices'

// AI Hub Parameters
@description('AI hub configuration')
param aiHubConfig object = {
  displayName: 'AI Hub for ${workloadName}'
  description: 'AI Hub for ${workloadName}'
}

// AI Project Parameters
@description('AI Project configuration')
param aiProjectConfig object = {
  displayName: 'AI Project for ${workloadName}'
  description: 'AI Project for document processing'
}

// Add tags parameter
@description('Tags to add to the resources')
param tags object

// Resource name generation
var resourceSuffix = uniqueString(resourceGroup().id, workloadName)
var names = {
  storage: 'st${resourceSuffix}'
  search: 'srch-${resourceSuffix}'
  aiAgent: 'ai-agent-${resourceSuffix}'
  aiContentUnderstanding: 'ai-cu-${resourceSuffix}'
  functionApp: 'func-${resourceSuffix}'
  appServicePlan: 'asp-${resourceSuffix}'
  staticWebApp: 'swa-${resourceSuffix}'
  appInsights: 'appi-${resourceSuffix}'
  logAnalytics: 'log-${resourceSuffix}'
  aiProject: 'ai-proj-${resourceSuffix}'
  aiHub: 'aihub-${resourceSuffix}'
}
var connections = {
  aiSearch: '${names.aiHub}-conn-aisearch'
  aiAgent: '${names.aiHub}-conn-aiagent'
  aiContentUnderstanding: '${names.aiHub}-conn-aicu'
  primary: aiServiceType == 'AIServices' ? '${names.aiHub}-conn-aiservices' : '${names.aiHub}-conn-aoai'
}

// Project connection string components
var projectConnection = {
  subscriptionId: subscription().subscriptionId
  resourceGroup: resourceGroup().name
  connectionString: '${primaryRegion}.api.azureml.ms;${subscription().subscriptionId};${resourceGroup().name};${names.aiProject}'
}


// TODO: Add queues for function app..

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: names.storage
  location: functionHostingRegion 
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
  name: names.search
  location: primaryRegion
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

// Azure AI Service - Content Understanding
resource aiContentUnderstandingService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: names.aiContentUnderstanding
  location: contentUnderstandingRegion
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: names.aiContentUnderstanding
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

// Azure AI Services - Agent Service
resource aiAgentService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: names.aiAgent
  location: primaryRegion
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: names.aiAgent
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
  parent: aiAgentService
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: gpt4ModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: gpt4ModelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Default'
  }
}

// Application Insights
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: names.logAnalytics
  location: primaryRegion
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: names.appInsights
  location: primaryRegion
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
  name: names.appServicePlan
  location: functionHostingRegion
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {}
}

// Role Assignments with Function App principal ID variable
var functionAppPrincipalId = reference(names.functionApp, '2022-09-01', 'full').identity.principalId

// Function App role assignments
resource functionStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, names.functionApp, blobDataContributor.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: blobDataContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionSearchAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, names.functionApp, searchContributor.id)
  scope: searchService
  properties: {
    roleDefinitionId: searchContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAiAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, names.functionApp, cognitiveServicesUser.id)
  scope: aiAgentService
  properties: {
    roleDefinitionId: cognitiveServicesUser.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionOpenAIAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, names.functionApp, openAIContributor.id)
  scope: aiAgentService
  properties: {
    roleDefinitionId: openAIContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionFileShareAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, names.functionApp, fileShareContributor.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: fileShareContributor.id
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: names.functionApp
  location: functionHostingRegion
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
          'https://${names.staticWebApp}.azurestaticapps.net'
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
          value: toLower(names.functionApp)
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
          value: aiAgentService.properties.endpoint
        }
        {
          name: 'AI_KEY'
          value: aiAgentService.listKeys().key1
        }
        {
          name: 'CO_AI_ENDPOINT'
          value: aiContentUnderstandingService.properties.endpoint
        }
        {
          name: 'CO_AI_KEY'
          value: aiContentUnderstandingService.listKeys().key1
        }
        {
          name: 'GPT_DEPLOYMENT_NAME'
          value: gpt4Deployment.name
        }
        {
          name: 'AI_PROJECT_CONNECTION_STRING'
          value: aiProject.tags.ProjectConnectionString
        }
        { 
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccount.name
        }
      ]
    }
  }
}

// Static Web App
resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: names.staticWebApp
  location: webHostingRegion
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

// Link function app to static web app - does this work cross region?
/*
resource staticWebAppBackend 'Microsoft.Web/staticSites/linkedBackends@2022-09-01' = {
  parent: staticWebApp
  name: 'backend'
  properties: {
    backendResourceId: functionApp.id
    region: primaryRegion
  }
}
*/

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

// Add Key Vault resource before AI Hub
resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' = {
  name: '${names.aiHub}-kv'
  location: primaryRegion
  tags: tags
  properties: {
    createMode: 'default'
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    enableRbacAuthorization: true
    enablePurgeProtection: true
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny'
    }
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: 7
    tenantId: subscription().tenantId
  }
}

// AI Hub resource
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-07-01-preview' = {
  name: names.aiHub
  location: primaryRegion
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiHubConfig.displayName
    description: aiHubConfig.description
    keyVault: keyVault.id
    storageAccount: storageAccount.id
    systemDatastoresAuthMode: 'identity'
  }
  kind: 'hub'

  resource aiServicesConnection 'connections@2024-07-01-preview' = {
    name: connections.primary
    properties: {
      category: aiServiceType
      target: aiAgentService.properties.endpoint
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: aiAgentService.id
        location: aiAgentService.location
      }
    }
  }

  resource searchServicesConnection 'connections@2024-07-01-preview' = {
    name: connections.aiSearch
    properties: {
      category: 'CognitiveSearch'
      target: 'https://${searchService.name}.search.windows.net'
      authType: 'AAD'
      isSharedToAll: true
      metadata: {
        ApiType: 'Azure'
        ResourceId: searchService.id
        location: searchService.location
      }
    }
  }

  resource capabilityHost 'capabilityHosts@2024-10-01-preview' = {
    name: '${names.aiHub}-host'
    properties: {
      capabilityHostKind: 'Agents'
    }
  }
}

// AI Project resource
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: names.aiProject
  location: primaryRegion
  tags: union(tags, {
    ProjectConnectionString: projectConnection.connectionString
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiProjectConfig.displayName
    description: aiProjectConfig.description
    hubResourceId: aiHub.id
  }
  kind: 'project'

  resource capabilityHost 'capabilityHosts@2024-10-01-preview' = {
    name: '${names.aiProject}-host'
    properties: {
      capabilityHostKind: 'Agents'
      aiServicesConnections: ['${connections.primary}']
      vectorStoreConnections: ['${connections.aiSearch}']
      storageConnections: ['${names.aiProject}/workspaceblobstore']
    }
  }
}

// Add role assignments for AI Project
module aiServiceRoleAssignments './ai-service-role-assignments.bicep' = {
  name: 'aiserviceroleassignments-${resourceSuffix}'
  params: {
    aiServicesName: aiAgentService.name
    aiProjectPrincipalId: aiProject.identity.principalId
    aiProjectId: aiProject.id
  }
}

module aiSearchRoleAssignments './ai-search-role-assignments.bicep' = {
  name: 'aisearchroleassignments-${resourceSuffix}'
  params: {
    aiSearchName: searchService.name
    aiProjectPrincipalId: aiProject.identity.principalId
    aiProjectId: aiProject.id
  }
}

resource aiProjectStorageQueueAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aiProject.name, storageQueueDataContributor.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageQueueDataContributor.id
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aiProjectStorageTableAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, aiProject.name, storageTableDataContributor.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageTableDataContributor.id
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageQueueDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'  // Storage Queue Data Contributor
}

resource storageTableDataContributor 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: resourceGroup()
  name: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'  // Storage Table Data Contributor
}

output endpoints object = {
  functionApp: {
    name: functionApp.name
    uri: functionApp.properties.defaultHostName
  }
  staticWebApp: {
    name: staticWebApp.name
    uri: staticWebApp.properties.defaultHostname
  }
  storage: storageAccount.name
  search: searchService.name
  aiAgent: aiAgentService.name
  aiContentUnderstanding: aiContentUnderstandingService.name
}

output aiConfiguration object = {
  project: {
    name: aiProject.name
    id: aiProject.id
    principalId: aiProject.identity.principalId
    workspaceId: aiProject.properties.workspaceId
    connectionString: aiProject.tags.ProjectConnectionString
  }
  hub: {
    id: aiHub.id
    connections: {
      search: connections.aiSearch
      agent: connections.aiAgent
      contentUnderstanding: connections.aiContentUnderstanding
    }
  }
}
