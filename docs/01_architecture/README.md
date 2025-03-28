# Overview of key Azure Services, overall Application Architecture and Codebase

## Introduction to Semantic Kernel, Azure Open AI, AI Foundry, and Cosmos DB
  
Semantic Kernel is a lightweight, open-source development kit that lets you easily build AI agents and integrate the latest AI models into your C#, Python, or Java codebase. It serves as an efficient middleware that enables rapid delivery of enterprise-grade solutions. Semantic Kernel combines prompts with existing APIs to perform actions, and it uses OpenAPI specifications to share extensions with other developers. It is designed to be future-proof, allowing you to swap out AI models without needing to rewrite your entire codebase. Here are some key points:
- Enterprise Ready: Trusted by Microsoft and other Fortune 500 companies, Semantic Kernel is flexible, modular, and secure. It supports telemetry and other security features, ensuring responsible AI solutions at scale.
- Automating Business Processes: It combines prompts with existing APIs to perform actions. By describing your existing code to AI models, Semantic Kernel translates model requests into function calls and returns the results.
- Modular and Extensible: You can add your existing code as plugins, maximizing your investment by integrating AI services through out-of-the-box connectors. It uses OpenAPI specifications, allowing you to share extensions with other developers.
 
Azure OpenAI is a service provided by Microsoft that allows businesses and developers to integrate powerful AI models into their applications using the Azure cloud platform. Here are some key points:
- Access to Advanced AI Models: Azure OpenAI provides access to state-of-the-art AI models, including GPT-4, which can be used for a variety of tasks such as natural language processing, translation, and more.
- Scalability and Reliability: Leveraging the Azure infrastructure, the service ensures high availability, scalability, and security, making it suitable for enterprise-level applications.
- Integration with Azure Services: Azure OpenAI can be seamlessly integrated with other Azure services like Azure Cognitive Services, Azure Machine Learning, and Azure Data Factory, enabling comprehensive AI solutions.
- Customization and Fine-Tuning: Users can customize and fine-tune AI models to better suit their specific needs, ensuring more accurate and relevant outputs.
- Compliance and Security: Azure OpenAI adheres to strict compliance standards and provides robust security features to protect data and ensure responsible AI usage.
  
Azure AI Foundry is a comprehensive platform provided by Microsoft that enables businesses and developers to create, deploy, and manage AI solutions. Here are some key points:
- End-to-End AI Development: Azure AI Foundry offers tools and services for the entire AI lifecycle, from data preparation and model training to deployment and monitoring.
- Integration with Azure Services: It seamlessly integrates with other Azure services like Azure Machine Learning, Azure Cognitive Services, and Azure Data Factory, providing a unified environment for AI development.
- Scalability and Flexibility: The platform is designed to handle large-scale AI projects, offering robust infrastructure and flexible deployment options to meet diverse business needs.
- Advanced AI Models: Users have access to cutting-edge AI models and can leverage pre-built solutions or customize models to suit specific requirements.
- Security and Compliance: Azure AI Foundry adheres to stringent security standards and compliance regulations, ensuring the protection of data and responsible AI usage.

Cosmos DB is a globally distributed, multi-model database service provided by Microsoft. Here are some key points:
- Global Distribution: Azure Cosmos DB allows you to distribute your data across multiple regions worldwide, ensuring high availability and low latency.
- Multi-Model Support: It supports various data models, including document, graph, key-value, and column-family, making it versatile for different types of applications.
- Scalability: The service offers automatic scaling of throughput and storage, allowing you to handle large amounts of data and high traffic seamlessly.
- Consistency Models: Azure Cosmos DB provides five consistency models (strong, bounded staleness, session, consistent prefix, and eventual), giving you control over the trade-off between consistency and performance.
- Comprehensive Security: It includes features like encryption at rest, network isolation, and compliance with industry standards to ensure data security.

## Introduction to AI Foundry's Evaluation Framework
## Integrating Azure Content Safety
## Ensuring secure and responsible AI practices
#### Overview of the app architecture
- Walkthrough of the codebase

---
#### Navigation: [Home](../../README.md) | [Next Section](../02_setup/README.md)