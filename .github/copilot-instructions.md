# GitHub Copilot Instructions

## Project Focus
When providing assistance, focus exclusively on the voice_agent project and ignore the video_agent, text_agent, and translator projects. The voice_agent is a real-time multi-modal & multi-domain agentic solution using Azure OpenAI's GPT-4o Realtime API for Audio.

## Key Areas to Consider

### Core Functionality
- Intent detection for seamless transitions between domain-specific agents
- Real-time voice AI agent using semantic_kernel for standardization
- Multi-domain approach using multi-agent architecture orchestrated with Semantic Kernel
- Integration with Azure OpenAI services, particularly GPT-4o-realtime-preview and GPT-4o-mini models

### Project Structure
Focus on the following key directories:
- `/voice_agent/app/`: Main application code
  - `/backend/`: Python backend services
  - `/frontend/`: TypeScript/React frontend
  - `/acs/`: Azure Communication Service integration
  - `/infra/`: Infrastructure and deployment files

### Documentation Reference
Refer to the documentation in the `/docs` folder which contains detailed information about:
- Architecture (01_architecture/)
- Setup procedures (02_setup/)
- Build instructions (03_build/)
- Deployment guidelines (04_deploy/)
- Exploration guides (05_explore/)

### Technical Components
When providing assistance, consider:
- Semantic Kernel integration
- Azure OpenAI services configuration
- Real-time audio processing
- Intent detection and agent switching
- Frontend/Backend communication
- Azure Communication Services integration

### Environment Configuration
Pay attention to the key environment variables and configurations in the voice_agent project:
- Azure OpenAI endpoints and API settings
- Model deployments (GPT-4o-realtime-preview, GPT-4o-mini)
- Intent detection settings
- Audio processing parameters

## Out of Scope
Ignore any questions or code related to:
- text_agent project
- video_agent project
- translator project
