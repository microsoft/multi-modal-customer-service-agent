### Chapter 5. Hands-On Exercises

#### PM / Developer Persona 
- Exercise 1:
   - add a new agent (car rental agent)
   - add data source for insurance policy / rental policies, etc. with AI Search
- Exercise 2: debug/fix/commit flow
  - scenario which 'fails' from a functionality standpoint -> use observability (tracing in AI Foundry), figure out the problem, change system-prompt/etc., run test suite (local run of Evaluations), then PR
  - artificial performance problem, and go through troubleshooting process

#### DevOps / SRE Persona
- Exercise 1: upgrade/change one of the agents' LLM to a new model/version (ex: going for gpt-4o to gpt4.5)  / run evaluations / azure monitor to check performance / APIM for costs
  - measure impact on generative quality, safety, cost, performance (latency)
  - Ref: https://techcommunity.microsoft.com/blog/azure-ai-services-blog/intelligent-load-balancing-with-apim-for-openai-weight-based-routing/4115155
  - (consider introducting https://learn.microsoft.com/en-us/azure/machine-learning/reference-model-inference-api?view=azureml-api-2&tabs=python to support multiple models under the same API) -> does it impact APIM functionality?
- Exercise 2: scale the system: ACS / APIM-AOAI
- Exercise 3: cost monitoring (cost per Agent Service Call)
- Exercise 4: genAI capacity scaling / showcase APIM switching workload to other AOAI endpoints based on capacity (simulate primary endpoint going out of capacity, ex: set Max TPM to 1k/mn tokens to saturate one endpoint)

#### Security/Safety Persona 
- Exercise 1: leverage of Evaluation SDK simulators to try to break the system and see if any extra safety needs to be put in place. https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data
- Exercise 2: one agent (new car rental agent) doesn't pass test above, fix it by adding filter -> retest -> PR
- Exercise 3: showcase that agents act using an identity that is tied to the logged in user and not a service principal -> demo that datastore access or service access prevents access to data not in scope of this identity
- (phase-2 / consider once this functionality is integrated into the AI Foundry Agent Service post Build 2025): Exercise 4: real-time monitoring around generative quality & safety (RAI)

#### Navigation: [Home](../../workshop.md) | [Previous Chapter](../chapter_04/README.md) | [Next Chapter](../chapter_06/README.md)
