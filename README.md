# Agentic RAG Solution Accelerator

A solution accelerator showcasing how to build agentic RAG applications using Azure AI Content Understanding and Azure AI Agent Service.

## Features

- 🤖 Azure AI Agent Service for intelligent chat interactions
- 📑 Content Understanding for document analysis
- 🔍 Vector and semantic search capabilities
- ⚡ Real-time file processing and chunking
- 🔄 Multiple document format support (PDF, audio, text)
- 🎨 Modern UI with FluentUI

## Architecture

The solution uses:
- Azure Functions for backend processing
- Azure AI Search for document storage and retrieval
- Azure Storage for file and configuration storage
- Azure Static Web Apps for frontend hosting
- Azure AI Services for models and content understanding

## Prerequisites

- Azure Subscription
- Node.js 18+
- Python 3.10+
- Azure CLI

## Quick Start
1. Clone the repository:
```bash
git clone https://github.com/aymenfurter/agentic-rag-solution-accelerator
cd agentic-rag-solution-accelerator
```

2. Deploy infrastructure:
```bash
az login
az deployment group create \
  --name agentic-rag-deployment \
  --resource-group your-resource-group \
  --template-file ./infra/main.bicep \
  --parameters ./infra/parameters.json
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Install frontend dependencies:
```bash
npm install
```

5. Start local development:
```bash
# Terminal 1: Start Functions
func start

# Terminal 2: Start frontend
npm start
```

## Configuration

Key environment variables:
- `STORAGE_CONNECTION_STRING`: Azure Storage connection string
- `SEARCH_ENDPOINT`: Azure AI Search endpoint
- `AI_ENDPOINT`: Azure AI Services endpoint
- More in `local.settings.json.example`

## Using the Solution

1. Visit the web application
2. Choose or create a template for your document processing
3. Upload documents
4. Start chatting with your documents!

## Customization

- Modify templates in `/templates`
- Adjust chunking strategies in `shared/chunking`
- Customize the agent prompts in setup function

## Contributing

Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

The workflow files provide:
1. Automated building and testing of both frontend and backend
2. Automated deployment to Azure
3. Infrastructure deployment using Bicep
4. Separate deployments for Function App and Static Web App

The README provides:
1. Clear project overview
2. Setup instructions
3. Architecture details
4. Configuration guidance
5. Usage instructions
6. Customization options

You'll need to set up these GitHub secrets:
- `AZURE_CREDENTIALS`
- `AZURE_SUBSCRIPTION`
- `AZURE_RG`
- `FUNCTION_APP_NAME`
- `STATIC_WEB_APP_TOKEN`