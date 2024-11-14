# Voice-Agent: An Application Pattern for multi-domain agents and the GPT-4o Realtime API for Audio

![Design pattern 1](app/backend/static/agent_pic.png)

## Demo
Watch this video for a demonstration of this pattern's core feature, using intent detection to seamlessly transition between domain specific agents, in addition to the agent specific features for knowledge retrieval and source system interaction.

https://github.com/user-attachments/assets/0b1c711a-efdc-4e69-8048-64f9d409e287

## Running this sample
We'll follow 4 steps to get this example running in your own environment: pre-requisites, creating an index, setting up the environment, and running the app.

### 1. Pre-requisites
You'll need instances of the following Azure services. You can re-use service instances you have already or create new ones.
1. [Azure OpenAI](https://ms.portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI), with 2 model deployments, one of the **gpt-4o-realtime-preview** model, a regular gpt-4o-mini model.
2. Train an intent_detection model with a SLM using Azure AI Studio. Check [the training data](./intent_detection_model)
### 2. Setting up the environment
The app needs to know which service endpoints to use for the Azure OpenAI and Azure AI Search. The following variables can be set as environment variables, or you can create a ".env" file in the "app/backend/" directory with this content.
   ```
AZURE_OPENAI_RT_ENDPOINT=wss://YOUR_OPENAI_INSTANCE.openai.azure.com
AZURE_OPENAI_RT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_RT_API_KEY=YOUR_KEY
AZURE_OPENAI_ENDPOINT="https://YOUR_OPENAI_INSTANCE.openai.azure.com/"
AZURE_OPENAI_API_KEY=YOUR_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION="2024-09-01-preview"
AZURE_OPENAI_EMB_DEPLOYMENT="text-embedding-ada-002"
INTENT_SHIFT_API_KEY=KEY_TO_DEPLOYED_DETECTION_MODEL
INTENT_SHIFT_API_URL=https://YOUR_DETECTION_ENDPOINT.westus2.inference.ml.azure.com/score
INTENT_SHIFT_API_DEPLOYMENT=NAME_OF_MODEL_DEPLOYMENT

   ```

### 4. Running the app

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

2. Clone the repo (`git clone https://github.com/microsoft/multi-modal-customer-service-agent`)
4. The app needs to know which service endpoints to use for the Azure OpenAI and Azure AI Search. The following variables can be set as environment variables, or you can create a ".env" file in the "app/backend/" directory with this content.
   ```
   AZURE_OPENAI_RT_ENDPOINT=wss://<your instance name>.openai.azure.com
   AZURE_OPENAI_RT_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_RT_API_KEY=<your api key>
   AZURE_OPENAI_ENDPOINT="https://<your regularinstance name>.openai.azure.com/"
   AZURE_OPENAI_API_KEY=<your api key>
   AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
   AZURE_OPENAI_API_VERSION="2024-09-01-preview"
   AZURE_OPENAI_EMB_DEPLOYMENT=<"text-embedding-ada-002" or the embedding deployment for policy question>
   INTENT_SHIFT_API_KEY=<your api key for the custom intent detection model>
   INTENT_SHIFT_API_URL=<your api URL for the custom intent detection model>
   INTENT_SHIFT_API_DEPLOYMENT=<your api deployment for the custom intent detection model>

   ```
5. Run this command to start the app:

   Windows:

   ```pwsh
   cd app
   pwsh .\start.ps1
   ```

   Linux/Mac:

   ```bash
   cd app
   ./start.sh
   ```

6. The app is available on http://localhost:8765


