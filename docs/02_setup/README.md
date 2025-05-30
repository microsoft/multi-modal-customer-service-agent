# Setup your Environment 

- [Running the sample locally](#running-this-sample-locally)
   - [Prerequisites](#prerequisites)
   - [Run in GitHub Codespaces](#run-in-github-codespaces)
   - [Run Locally](#run-in-local-environment)
- [Deploy to Azure](#deploy-to-azure-using-azd)

## Running this sample locally

After completing the prerequesites choose one of the options to run the sample locally.

### Prerequisites

You'll need instances of the following Azure services. You can re-use service instances you have already or create new ones.

1. [Azure OpenAI](https://ms.portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI), with 2 model deployment: 
   1. **gpt-4o-realtime-preview** model, named "gpt-4o-realtime-preview"
   1. **gpt-4o-mini** model
1. [Optional] Train an intent_detection model with a SLM using Azure AI Studio. Check [the training data](./intent_detection_model)

### Run in GitHub Codespaces

You can run this repo virtually by using GitHub Codespaces, which will open a web-based VS Code in your browser:

[![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&skip_quickstart=true&machine=basicLinux32gb&repo=840462613&devcontainer_path=.devcontainer%2Fdevcontainer.json&geo=WestUs2)

Once the codespace opens (this may take several minutes), open a new terminal.

1. Setting up the environment

   The app needs to know which service endpoint to use for the Azure OpenAI. Set the following variables in the ".env" file in the "app/backend/" directory with the values from your Azure OpenAI resource.

   ```bash
   # Azure OpenAI settings
   AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
   AZURE_OPENAI_API_KEY=<your-api-key>
   AZURE_OPENAI_4O_MINI_DEPLOYMENT=<your-azure-openai-4o-mini-deployment-name>
   AZURE_OPENAI_EMB_DEPLOYMENT=<your-text-embedding-ada-002-deployment-name> # must be model type: text-embedding-ada-002
   ```
   [Optional] The voice agent can use a fine-tuned SLM deployment to classify intent to minimize latency. If you do not have this deployment available then you can use the Azure OpenAI **gpt-4o-mini** deployment, which is fast enough to classify intent with minimal impact on latency. To use **gpt-4o-mini** leave the `INTENT_SHIFT_API_*` env variables empty.

1. Running the app

   In the terminal run this command to start the app:

   ```bash
   cd voice_agent/app
   ./start.sh
   ```
1. Once the scripts completes, click on the link in the terminal to open the app in the browser: http://127.0.0.1:5173/

### Run in Local environment

1. Install the required tools:
   - [Node.js](https://nodejs.org/en)
   - [Python >=3.11](https://www.python.org/downloads/)
      - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
      - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`.
   - [Powershell](https://learn.microsoft.com/powershell/scripting/install/installing-powershell)

1. Clone the repo (`git clone https://github.com/microsoft/multi-modal-customer-service-agent`)
1. The app needs to know which service endpoint to use for the Azure OpenAI. Copy the .env.sample file in the "app/backend/" directory into a new .env file in the same directory and set the following variables with the values from your Azure OpenAI resource.

   ```bash
   # Azure OpenAI settings
   AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
   AZURE_OPENAI_API_KEY=<your-api-key>
   AZURE_OPENAI_4O_MINI_DEPLOYMENT=<your-azure-openai-4o-mini-deployment-name>
   AZURE_OPENAI_EMB_DEPLOYMENT=<your-text-embedding-ada-002-deployment-name> # must be model type: text-embedding-ada-002
   ```

   [Optional] The voice agent can use a fine-tuned SLM deployment to classify intent to minimize latency. If you do not have this deployment available then you can use the Azure OpenAI **gpt-4o-mini** deployment, which is fast enough to classify intent with minimal impact on latency. To use **gpt-4o-mini** leave the `INTENT_SHIFT_API_*` env variables empty.

1. Run this command to start the app:

   Windows:

   ```pwsh
   cd voice_agent\app
   pwsh .\start.ps1
   ```

   Linux/Mac:

   ```bash
   cd voice_agent/app
   ./start.sh
   ```

1. Once the scripts completes, click on the link in the terminal to open the app in the browser: http://127.0.0.1:5173/

## Deploy to Azure using azd
You can deploy this sample to Azure using the [Azure Developer CLI (`azd`)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/).

1. Download and install [azd](https://aka.ms/azd/install) (Azure Developer CLI)

1. Change directory to:

   ```bash
   cd voice_agent/app
   ```

1. Execute this command:

   ```bash
   azd up
   ```

1. When prompted provided the following names:
   1. Environment name (used as the name of the new or existing resource group to deploy into)
   1. Azure Subscription to use
   1. Azure location to use

---
#### Navigation: [Home](../../README.md) | [Previous Section](../01_architecture/README.md) | [Next Section](../03_observability/README.md)