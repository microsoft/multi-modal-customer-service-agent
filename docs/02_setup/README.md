# Setup your Environment 

## Running this sample

We'll follow 4 steps to get this example running in your own environment: pre-requisites, creating an index, setting up the environment, and running the app.

### Pre-requisites

You'll need instances of the following Azure services. You can re-use service instances you have already or create new ones.

1. [Azure OpenAI](https://ms.portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI), with 2 model deployments, one of the **gpt-4o-realtime-preview** model, a regular **gpt-4o-mini** model.
1. [Optional] Train an intent_detection model with a SLM using Azure AI Studio. Check [the training data](./intent_detection_model)

### Setting up the environment

The app needs to know which service endpoints to use for the Azure OpenAI and Azure AI Search. The following variables can be set as environment variables, or you can create a ".env" file in the "app/backend/" directory with this content.

The voice agent can use a fine-tuned SLM deployment to classify intent to minimize latency. If you do not have this deployment available then you can use the Azure OpenAI **gpt-4o-mini** deployment, which is fast enough to classify intent with minimal impact on latency. To use **gpt-4o-mini** leave the `INTENT_SHIFT_API_*` env variables empty and supply `AZURE_OPENAI_4O_MINI_DEPLOYMENT`.

```bash
AZURE_OPENAI_ENDPOINT="https://.openai.azure.com/"
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-10-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMB_DEPLOYMENT="text-embedding-ada-002"
AZURE_OPENAI_EMB_ENDPOINT= [Optional] if different from your realtime endpoint
AZURE_OPENAI_EMB_API_KEY= [Optional] if providing an embedding endpoint
AZURE_OPENAI_4O_MINI_DEPLOYMENT=YOUR_AZURE_OPENAI_4O_MINI_DEPLOYMENT_NAME
INTENT_SHIFT_API_KEY=
INTENT_SHIFT_API_URL=https://YOUR_ML_DEPLOYMENT.westus2.inference.ml.azure.com/score
INTENT_SHIFT_API_DEPLOYMENT=YOUR_ML_DEPLOYMENT_NAME
AZURE_OPENAI_API_VERSION=2024-10-01-preview
AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview
```

### Running the app

#### GitHub Codespaces

You can run this repo virtually by using GitHub Codespaces, which will open a web-based VS Code in your browser:

[![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&skip_quickstart=true&machine=basicLinux32gb&repo=840462613&devcontainer_path=.devcontainer%2Fdevcontainer.json&geo=WestUs2)

Once the codespace opens (this may take several minutes), open a new terminal.

#### VS Code Dev Containers

You can run the project in your local VS Code Dev Container using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/multi-modal-customer-service-agent)
3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a new terminal.

#### Local environment

1. Install the required tools:
   - [Node.js](https://nodejs.org/en)
   - [Python >=3.11](https://www.python.org/downloads/)
      - **Important**: Python and the pip package manager must be in the path in Windows for the setup scripts to work.
      - **Important**: Ensure you can run `python --version` from console. On Ubuntu, you might need to run `sudo apt install python-is-python3` to link `python` to `python3`.
   - [Powershell](https://learn.microsoft.com/powershell/scripting/install/installing-powershell)

1. Clone the repo (`git clone https://github.com/microsoft/multi-modal-customer-service-agent`)
1. Ensure env variables are set per [Setting up the environment](#2-setting-up-the-environment)
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

1. The app is available on http://localhost:8765

#### Deploy to Azure using azd

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