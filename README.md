# Real-time Multi-modal & Multi-domain Agentic Solution Accelerator in Azure

## Overview

This repository demonstrates a production-grade approach to deliver a real-time multi-modal & multi-domain agentic solution in Azure. The multi-domain approachs relies on a multi-agent archtecture orchestrated with Semantic Kernel and facilitate scaling a solution as business needs grow. It also demonstrates the key components and patterns to handle monitoring, security, safety, scalability and overall ease of maintenance from troubleshooting to deployment, migration of models and remediation of issues.

This solution articulates these concepts around a real-time voice/video/text Agent supporting a booking agency (flights and hotels). The customer service function assists registered customers in modifying their hotel and flight bookings, confirming reservations, and addressing inquiries about hotel and flight policies.

The solution is designed to be extensible, allowing for the addition of new agents and domains as needed. The architecture is built on Azure services, including Azure OpenAI Service, Azure Foundry, Azure Cosmos DB, Azure Container Apps and others.
  
NOTE: [Check out this blog post for more details](https://techcommunity.microsoft.com/blog/machinelearningblog/automating-real-time-multi-modal-customer-service-with-ai/4354892)

## Demo

Watch this video for a demonstration of the multi-domain design in action. Intent detection is used to transition between the domain specific agents behind the scenes creating a seamless customer experience.

https://github.com/user-attachments/assets/0b1c711a-efdc-4e69-8048-64f9d409e287


## Deep Dive

### [Overview of key Azure Services, overall Application Architecture and Codebase](docs/01_architecture/README.md)

Visit this section to get an overview of the overall architecture and patterns, understand the key Azure services used in the application and how the codebase is structured and get a better understanding of Semantic Kernel, Azure Open AI, AI Foundry and Cosmos DB. You will also get to discover some key frameworks like the Azure AI Foundry's Evaluation Framework and Azure Content Safety. Finally, a quick overview of the codebase will help you understand how the app is structured and how to navigate it.

### [Setup your Environment](docs/02_setup/README.md)

Proceed to this section if you'd like to setup your local development environment. You will install the required tools and libraries, clone the prebuilt app repository, and set up your development environment.

You will also set up the Azure Landing Zone to host the application once deployed.

### [Build and Run the App Locally](docs/03_build/README.md)

In this section, you will get the instructions to build and run the backend (Python) and frontend (React.js) of the app locally. You will understand how to test the app locally to ensure everything is working as expected.

### [Deploy to Azure](docs/04_deploy/README.md)

Visit this section to get the detailed instructions to deploy the application front end and backend services to Azure and proceed with some basic tests to ensure everything is working as expected.

### [Explore this Solution Accelerator with Guided Exercises](docs/05_explore/README.md)

The purpose of this section is to help you learn how to best leverage this solution by walking you through some key scenarios related to different personas involved in the lifecycle of a complex Agentic AI solution. For instance, learn how to add new features to the app, scale it, secure it, monitor and troubleshoot it.

You will experience the benefits of a production-grade AI application when it comes to speed of innovation, maintainability and scalability.

This is a great way to get familiar with the solution and understand how to best leverage it for your own use cases.