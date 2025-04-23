# Explore this Solution Accelerator with Guided Exercises

## PM / Developer Persona 
### Exercise 1:  Add a new agent (car rental agent)
1.  First, create a new car rental tools plugin.  Create file car_rental_plugins.py in voice_agent\app\backend\agents\tools and add the following code:

```python
     from typing import List
     from semantic_kernel import Kernel
     from semantic_kernel.skill_definition import sk_function
     
     class Car_Rental_Tools:
         """Tools for car rental agent to perform various rental operations"""
     
         @sk_function(
             description="Search for available rental cars",
             name="search_cars"
         )
         async def search_cars(self, location: str, pickup_date: str, return_date: str) -> str:
             # Mock implementation - replace with actual car rental API
             return f"Found available cars in {location} from {pickup_date} to {return_date}: \n" \
                    "1. Economy - Toyota Corolla ($45/day)\n" \
                    "2. SUV - Honda CR-V ($65/day)\n" \
                    "3. Luxury - BMW 5 Series ($95/day)"
     
         @sk_function(
             description="Get rental car details",
             name="get_car_details"
         )
         async def get_car_details(self, car_id: str) -> str:
             # Mock implementation
             car_details = {
                 "1": "Toyota Corolla: 4 doors, 5 seats, automatic transmission, GPS, bluetooth",
                 "2": "Honda CR-V: 5 doors, 5 seats, automatic transmission, GPS, bluetooth, roof rack",
                 "3": "BMW 5 Series: 4 doors, 5 seats, automatic transmission, GPS, bluetooth, leather seats"
             }
             return car_details.get(car_id, "Car not found")  
```

2. Create a car rental agent profile.  Create car_rental_agent_profile.yaml in voice_agent\app\backend\agents\agent_profiles and add the following:

    ```python
      name: car_rental_agent
      default_agent: false
      persona: |
          You are a helpful car rental agent assisting {customer_name} (ID: {customer_id}).
          Your role is to help customers find and book rental cars that match their needs.
          
          Key responsibilities:
          - Search for available rental cars based on location and dates
          - Provide detailed information about specific vehicles
          - Explain rental policies and requirements
          - Help with booking process
          
          Always be professional and courteous while providing accurate information.
    ```
3. Modify the RTMiddleTier class to include the new car rental agent.  Add the following to the _load_agents method of voice_agent\app\backend\rtmt.py:

  ```python
    from agents.tools.car_rental_plugins import Car_Rental_Tools
  ```

```python
   # ...existing code...
    def _load_agents(self):
        base_path = "agents/agent_profiles"
        agent_profiles = [f for f in os.listdir(base_path) if f.endswith("_profile.yaml")]
        for profile in agent_profiles:
            profile_path = os.path.join(base_path, profile)
            with open(profile_path, "r") as file:
                try:
                    data = yaml.safe_load(file)
                    self.agents.append(data)
                    agent_name = data.get("name")
                    self.kernels[agent_name] = Kernel()
                    if agent_name == "hotel_agent":
                        self.kernels[agent_name].add_plugin(
                            plugin=Hotel_Tools(),
                            plugin_name="hotel_tools",
                            description="tools for hotel agent"
                        )
                    elif agent_name == "flight_agent":
                        self.kernels[agent_name].add_plugin(
                            plugin=Flight_Tools(),
                            plugin_name="flight_tools",
                            description="tools for flight agent"
                        )
                    elif agent_name == "car_rental_agent":  # Add this section
                        self.kernels[agent_name].add_plugin(
                            plugin=Car_Rental_Tools(),
                            plugin_name="car_rental_tools",
                            description="tools for car rental agent"
                        )
      # ...existing code...

 ```
4.  Next steps are to update the system message to include the car rental agent along with the intent detection functionality.  Update the utility.py detect_intent method to now include car rental agent as part of the system message.  Add the below code to the messages block.

```python
  - **car_rental_agent**: Deal with car rentals, vehicle reservations, changes, and general car rental policy questions.
```
The intent detection functionality has already been updated to recognize car rental related queries.   Please review the intent detention model for more information.  

5. Let's add data source for insurance policy / rental policies, etc. with AI Search

Create a JSON file for car rental policies.  Name the file car_rental_policy.json and store it in the data folder along with the flight & hotel policies:

```python
[
    {
        "id": "insurance_basic",
        "policy_text": "Basic insurance coverage is mandatory and includes: Collision Damage Waiver (CDW), Third Party Liability (TPL), and Personal Accident Insurance (PAI). Daily rate varies by vehicle class.",
        "policy_text_embedding": null
    },
    {
        "id": "insurance_premium",
        "policy_text": "Premium insurance package includes basic coverage plus: Zero deductible, Tire and glass coverage, Personal effects coverage, and Roadside assistance. Available for an additional $15/day.",
        "policy_text_embedding": null
    },
    {
        "id": "rental_requirements",
        "policy_text": "Renters must be at least 21 years old, possess a valid driver's license, and present a major credit card. Additional fees apply for drivers under 25.",
        "policy_text_embedding": null
    }
]
```
Update the plugin to setup Azure OpenAI client for embeddings, create get_embedding method to generate text embeddings.  Define the SearchClient class with semantic search functionality and finally initialize the search client.

```python
  # Azure OpenAI client setup  
  embedding_client = AzureOpenAI(  
      api_key=AZURE_OPENAI_EMB_API_KEY,  
      azure_endpoint=AZURE_OPENAI_EMB_ENDPOINT,  
      api_version="2023-12-01-preview"  
  )  

  def get_embedding(text: str, model: str = AZURE_OPENAI_EMB_DEPLOYMENT) -> list[float]:  
      """Generate text embeddings using Azure OpenAI."""  
      text = text.replace("\n", " ")  
      return embedding_client.embeddings.create(input=[text], model=model).data[0].embedding  

  class SearchClient:  
      """Client for performing semantic search on a knowledge base."""  
      def __init__(self, emb_map_file_path: str):  
          with open(emb_map_file_path) as file:  
              self.chunks_emb = json.load(file)  
    
      def find_article(self, question: str, topk: int = 3) -> str:  
          """Find relevant articles based on cosine similarity."""  
          input_vector = get_embedding(question)  
          cosine_list = [  
              (item['id'], item['policy_text'], 1 - spatial.distance.cosine(input_vector, item['policy_text_embedding']))  
              for item in self.chunks_emb  
          ]  
          cosine_list.sort(key=lambda x: x[2], reverse=True)  
          cosine_list = cosine_list[:topk]  
    
          return "\n".join(f"{chunk_id}\n{content}" for chunk_id, content, _ in cosine_list)  

  # Initialize the search client
  search_client = SearchClient("./data/car_rental_policy.json")

```

Update the Car_Rental_Tools class to include policy search:

```python
    from openai import AzureOpenAI
    import json
    from scipy import spatial
```

```python

    @kernel_function(
        name="search_rental_policies",
        description="Search car rental and insurance policies for relevant information."
    )
    async def search_rental_policies(self, 
        search_query: Annotated[str, "The search query about rental or insurance policies."]
    ) -> str:
        return search_client.find_article(search_query)
```
Create an embedding generation script & store it in a ./scripts/generate_car_rental_policy_embeddings.py :

```python
  import json
  from openai import AzureOpenAI
  import os
  from dotenv import load_dotenv

  load_dotenv()

  def generate_embeddings(input_file: str):
      """Generate embeddings for policy documents."""
      client = AzureOpenAI(
          api_key=os.getenv("AZURE_OPENAI_EMB_API_KEY"),
          azure_endpoint=os.getenv("AZURE_OPENAI_EMB_ENDPOINT"),
          api_version="2023-12-01-preview"
      )

      # Load the JSON file
      with open(input_file, 'r') as file:
          data = json.load(file)

      # Generate embeddings for each policy text
      for item in data:
          response = client.embeddings.create(
              input=[item['policy_text']],
              model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
          )
          item['policy_text_embedding'] = response.data[0].embedding

      # Save the updated JSON with embeddings
      output_file = input_file
      with open(output_file, 'w') as file:
          json.dump(data, file, indent=2)

  if __name__ == "__main__":
      generate_embeddings("./data/car_rental_policy.json")

```
Run the embedding generation script in the terminal 
```
  cd c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend
  python scripts/generate_car_rental_policy_embeddings.py
```

The car rental policy search uses the same semantic search approach as the hotel policies.  The policies are stored in JSON format with embeddings for efficient semantic search.

The Car_Rental_Tools class now includes a method to search policies.

The embedding generation script needs to be run once to prepare the policy data.

You can expand the policy database by adding more entries to the JSON file.

After implementing these changes:

- The car rental agent will be available alongside the hotel and flight agents
- The agent can be triggered through intent detection
- The agent will have access to car rental specific tools through its plugin
- The agent will maintain its own context and persona while handling customer interactions
       
Test the new agent with various car rental scenarios.

Future steps to try on your own.
- Expand the Car_Rental_Tools class with additional functions as needed.  
- Replace mock implementations with actual car rental API integrations

### Exercise 2: debug/fix/commit flow
  - scenario which 'fails' from a functionality standpoint -> use observability (tracing in AI Foundry), figure out the problem, change system-prompt/etc., run test suite (local run of Evaluations), then PR
  - artificial performance problem, and go through troubleshooting process

## DevOps / SRE Persona
- Exercise 1: upgrade/change one of the agents' LLM to a new model/version (ex: going for gpt-4o to gpt4.5)  / run evaluations / azure monitor to check performance / APIM for costs
  - measure impact on generative quality, safety, cost, performance (latency)
  - Ref: https://techcommunity.microsoft.com/blog/azure-ai-services-blog/intelligent-load-balancing-with-apim-for-openai-weight-based-routing/4115155
  - (consider introducting https://learn.microsoft.com/en-us/azure/machine-learning/reference-model-inference-api?view=azureml-api-2&tabs=python to support multiple models under the same API) -> does it impact APIM functionality?
- Exercise 2: scale the system: ACS / APIM-AOAI
- Exercise 3: cost monitoring (cost per Agent Service Call)
- Exercise 4: genAI capacity scaling / showcase APIM switching workload to other AOAI endpoints based on capacity (simulate primary endpoint going out of capacity, ex: set Max TPM to 1k/mn tokens to saturate one endpoint)

## Security/Safety Persona 
- Exercise 1: leverage of Evaluation SDK simulators to try to break the system and see if any extra safety needs to be put in place. https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data
- Exercise 2: one agent (new car rental agent) doesn't pass test above, fix it by adding filter -> retest -> PR
- Exercise 3: showcase that agents act using an identity that is tied to the logged in user and not a service principal -> demo that datastore access or service access prevents access to data not in scope of this identity
- (phase-2 / consider once this functionality is integrated into the AI Foundry Agent Service post Build 2025): Exercise 4: real-time monitoring around generative quality & safety (RAI)

---
#### Navigation: [Home](../../README.md) | [Previous Section](../04_deploy/README.md)
