# Explore this Solution Accelerator with Guided Exercises

## PM / Developer Persona 
### Exercise 1:  Add a new agent (car rental agent)
1.  First, create a new car rental tools plugin.  Create file car_rental_plugins.py in voice_agent\app\backend\agents\tools and add the following code:

    <details>
    <summary> Click to expand/collaspse</summary>

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
</details>

2. Create a car rental agent profile.  Create car_rental_agent_profile.yaml in voice_agent\app\backend\agents\agent_profiles and add the following:

    <details>
    <summary> Click to expand/collaspse</summary>

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

    </details>

3. Modify the RTMiddleTier class to include the new car rental agent.  Add the following to the _load_agents method of voice_agent\app\backend\rtmt.py:

    <details>
    <summary> Click to expand/collaspse</summary>

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

</details>

4.  Next steps are to update the system message to include the car rental agent along with the intent detection functionality.  Update the utility.py detect_intent method to now include car rental agent as part of the system message.  Add the below code to the messages block.

    <details>
    <summary> Click to expand/collaspse</summary>

    ```python
    - **car_rental_agent**: Deal with car rentals, vehicle reservations, changes, and general car rental policy questions.
    ```

    </details>

    Note:  The intent detection functionality has already been updated to recognize car rental related queries.   Please review the intent detention model for more information.  

5. Let's add data source for insurance policy / rental policies, etc. with AI Search

    Create a JSON file for car rental policies.  Name the file car_rental_policy.json and store it in the data folder along with the flight & hotel policies:

    <details>
    <summary> Click to expand/collaspse</summary>

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

    </details>


    Update the plugin to setup Azure OpenAI client for embeddings, create get_embedding method to generate text embeddings.  Define the SearchClient class with semantic search functionality and finally initialize the search client.

    <details>
    <summary> Click to expand/collaspse</summary>

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

    </details>

    Update the Car_Rental_Tools class to include policy search:

    <details>
    <summary> Click to expand/collaspse</summary>

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


    </details>

    Create an embedding generation script & store it in  ./scripts/generate_car_rental_policy_embeddings.py :

    <details>
    <summary> Click to expand/collaspse</summary>

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


    </details>


    Run the embedding generation script in the terminal 

    <details>
    <summary> Click to expand/collaspse</summary>

    ```
    cd c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend
    python scripts/generate_car_rental_policy_embeddings.py
    ```

    </details>

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

### Exercise 1: Upgrade the Flight Agent’s LLM and Evaluate with Azure AI Evaluation SDK

#### Objective
Upgrade the LLM used by the flight_agent in the voice_agent project (e.g., from gpt-4 to gpt-4o), and evaluate the impact using the Azure AI Evaluation SDK for Python.

#### Files to Update or Create
- `voice_agent/app/backend/tests/test_flight_agent_evaluation.py` (new)

---

I've created two test files to help you implement agent evaluation using the Azure AI Foundry evaluation SDK as requested:

1. **test_flight_agent_evaluation.py**: A basic evaluation script that tests the flight agent against predefined test cases. 

This file contains:

- Setup for the IntentResolutionEvaluator, ToolCallAccuracyEvaluator, and TaskAdherenceEvaluator
- Tool definitions that match your flight_agent's capabilities
- A set of example test cases covering different flight-related scenarios
- Individual evaluation logic for each metric

2. **test_flight_agent_integration.py**: A more advanced integration test that demonstrates:

- How to connect to an Azure AI Foundry project for more detailed evaluation
- Both individual and batch evaluation workflows
- An example of how to record and evaluate real agent interactions
- Support for visualizing results in the Azure AI Foundry portal


To run these evaluations, you'll need to configure a few environment variables:

```
    AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
    AZURE_OPENAI_API_KEY=your_azure_openai_api_key
    AZURE_OPENAI_API_VERSION=2024-10-01-preview
    AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini (or your preferred model)
```

For the integration with Azure AI Foundry, you'll also need these variables:

```
    PROJECT_CONNECTION_STRING=your_project_connection_string
    AZURE_SUBSCRIPTION_ID=your_subscription_id
    PROJECT_NAME=your_project_name
    RESOURCE_GROUP_NAME=your_resource_group_name
```
To run the tests, you can use:

```
    cd voice_agent/app/backend
    python -m tests.test_flight_agent_evaluation
    python -m tests.test_flight_agent_integration
```

The evaluators will assess your flight agent's performance in three key areas:

- Intent Resolution: Measures how well the agent understands the user's request, including identifying when to use the right tools.

- Tool Call Accuracy: Evaluates whether the agent is using the appropriate tools and passing the correct parameters based on the user's request.

- Task Adherence: Measures how well the agent's responses align with its assigned tasks as a flight agent.

These evaluations will help you identify areas for improvement in your flight agent and ensure it's effectively handling customer inquiries according to its design.

#### Step 1: Create an Evaluation Script

**File:** `voice_agent/app/backend/tests/test_flight_agent_evaluation.py`

Setup four test cases covering different flight scenarios:
- Flight booking inquiry
- Baggage policy question
- Flight change request
- Flight status check

```python



```








#### Step 1: Update the LLM Model for Flight Agent

**File:** `voice_agent/app/backend/rtmt.py`





---

#### Step 2: Update the `.env` File

**File:** `.env`

Add or update these lines:

```
AZURE_OPENAI_FLIGHT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_ENDPOINT=https://<your-endpoint>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
```

---

#### Step 3: Install Azure AI Evaluation SDK

Install the Azure AI Evaluation SDK 
```
pip install azure-ai-evaluation
pip install azure-ai-projects
```

**File:** `voice_agent/app/backend/requirements.txt`

Or add this line:

```
azure-ai-evaluation
azure-ai-projects
```

Then install:

```pwsh
pip install -r voice_agent/app/backend/requirements.txt
```

---

#### Step 4: Create an Evaluation Script

**File:** `voice_agent/app/backend/tests/test_flight_agent_evaluation.py`

Create this file with the following content:

```python
import os
from azure.ai.evaluation import EvaluationClient, EvaluationTask, EvaluationScenario

# Load environment variables
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize the evaluation client
client = EvaluationClient(endpoint=endpoint, api_key=api_key)

# Define a scenario to test the flight agent
scenario = EvaluationScenario(
    name="FlightAgentLLMUpgrade",
    description="Evaluate upgraded LLM for flight agent",
    tasks=[
        EvaluationTask(
            input_data={"user_query": "Book a flight from New York to London on May 10th"},
            expected_output="Flight booking details for New York to London on May 10th"
        ),
        EvaluationTask(
            input_data={"user_query": "What is the baggage allowance for economy class?"},
            expected_output="Baggage allowance details for economy class"
        ),
        # Add more tasks as needed
    ]
)

# Run the evaluation
results = client.evaluate(scenario)
print(results)
```

---

#### Step 5: Test the Flight Agent

Restart your backend if needed, then run the evaluation script:

```pwsh
python voice_agent/app/backend/tests/test_flight_agent_evaluation.py
```

Check the output to see the results of the upgraded LLM.

---

#### Step 6: (Optional) Compare with Previous Model

To compare, set `AZURE_OPENAI_FLIGHT_DEPLOYMENT` in `.env` to the old model (e.g., `gpt-4`), rerun the evaluation, and compare outputs.

---

**Summary of files to update/create:**
- `voice_agent/app/backend/rtmt.py` (update LLM config)
- `.env` (set deployment/model info)
- `voice_agent/app/backend/requirements.txt` (add evaluation SDK)
- `voice_agent/app/backend/tests/test_flight_agent_evaluation.py` (new evaluation script)

## Security/Safety Persona 
- Exercise 1: leverage of Evaluation SDK simulators to try to break the system and see if any extra safety needs to be put in place. https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data
- Exercise 2: one agent (new car rental agent) doesn't pass test above, fix it by adding filter -> retest -> PR
- Exercise 3: showcase that agents act using an identity that is tied to the logged in user and not a service principal -> demo that datastore access or service access prevents access to data not in scope of this identity
- (phase-2 / consider once this functionality is integrated into the AI Foundry Agent Service post Build 2025): Exercise 4: real-time monitoring around generative quality & safety (RAI)

---
#### Navigation: [Home](../../README.md) | [Previous Section](../04_deploy/README.md)
