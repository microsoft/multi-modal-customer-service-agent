# Use the Python 3.12 base image
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Install Azure CLI
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends ca-certificates curl apt-transport-https lsb-release gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -sLS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=`dpkg --print-architecture` signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/azure-cli.list \
    && apt-get update \
    && apt-get -y install azure-cli \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm

# Install Azure Developer CLI (azd)
RUN curl -fsSL https://aka.ms/install-azd.sh | bash

# Set environment variables
ENV ASPIRE_DASHBOARD_ENDPOINT=http://aspire-dashboard:18889

# Create the workspace folder
RUN mkdir -p /workspaces/multi-modal-customer-service-agent

WORKDIR /workspaces/multi-modal-customer-service-agent

# Keep the container running
CMD ["sleep", "infinity"]
