# Explore this Solution Accelerator with Guided Exercises

## PM / Developer Persona 
- Exercise 1:
   - add a new agent (car rental agent)
   - 1.  First, create a new car rental tools plugin:
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
         def search_cars(self, location: str, pickup_date: str, return_date: str) -> str:
             # Mock implementation - replace with actual car rental API
             return f"Found available cars in {location} from {pickup_date} to {return_date}: \n" \
                    "1. Economy - Toyota Corolla ($45/day)\n" \
                    "2. SUV - Honda CR-V ($65/day)\n" \
                    "3. Luxury - BMW 5 Series ($95/day)"
     
         @sk_function(
             description="Get rental car details",
             name="get_car_details"
         )
         def get_car_details(self, car_id: str) -> str:
             # Mock implementation
             car_details = {
                 "1": "Toyota Corolla: 4 doors, 5 seats, automatic transmission, GPS, bluetooth",
                 "2": "Honda CR-V: 5 doors, 5 seats, automatic transmission, GPS, bluetooth, roof rack",
                 "3": "BMW 5 Series: 4 doors, 5 seats, automatic transmission, GPS, bluetooth, leather seats"
             }
             return car_details.get(car_id, "Car not found")  
      ```

2. Create a car rental agent profile:
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
3. Modify the RTMiddleTier class to include the new car rental agent.  Add this to the _load_agents method:
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
      After implementing these changes:

         The car rental agent will be available alongside the hotel and flight agents
         The agent can be triggered through intent detection
         The agent will have access to car rental specific tools through its plugin
         The agent will maintain its own context and persona while handling customer interactions
         Make sure to:
         
         Update your intent detection model to recognize car rental related queries
         Test the new agent with various car rental scenarios
         Expand the Car_Rental_Tools class with additional functions as needed
         Replace mock implementations with actual car rental API integrations
   - add data source for insurance policy / rental policies, etc. with AI Search
- Exercise 2: debug/fix/commit flow
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
