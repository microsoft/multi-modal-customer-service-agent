# Explore this Solution Accelerator with Guided Exercises

## PM / Developer Persona 
### Exercise 1:  Add a new agent (car rental agent)
1.  First, create a new car rental tools plugin.  Create file car_rental_plugins.py in voice_agent\app\backend\agents\tools and add the following code:

    <details>
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

    ```python
    - **car_rental_agent**: Deal with car rentals, vehicle reservations, changes, and general car rental policy questions.
    ```

    </details>

    Note:  The intent detection functionality has already been updated to recognize car rental related queries.   Please review the intent detention model for more information.  

5. Let's add data source for insurance policy / rental policies, etc. with AI Search

    Create a JSON file for car rental policies.  Name the file car_rental_policy.json and store it in the data folder along with the flight & hotel policies:

    <details>
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

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
    <summary> Click to expand/collapse</summary>

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

### Exercise 1: Upgrade the Flight Agent's LLM and Evaluate with Azure AI Evaluation SDK

#### Objective
For the flight_agent in the voice_agent project, evaluate the current LLM.  Then upgrade the LLM (e.g., from gpt-4 to gpt-4o) and evaluate the impact using the Azure AI Evaluation SDK for Python.

#### Prerequisites
- Basic understanding of Python and VS Code
- Access to Azure OpenAI resources
- Understanding of LLM evaluation concepts

#### Steps Overview

1. Review current LLM 
2. Install required packages
3. Create & understand the evaluation script
4. Run the evaluation
5. Analyze results
6. Upgrade the LLM
7. Rerun the evaluation
8. Analyze and compare results between the runs

#### Step 1: Review current LLM

Review the current LLM environment variable.  It is in a `.env` file in the backend directory.

```
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
```

#### Step 2: Install Required Packages

Install the Azure AI Evaluation SDK:

```bash
pip install azure-ai-evaluation dotenv
```

Or add these lines to `voice_agent/app/backend/requirements.txt`:

```
azure-ai-evaluation
python-dotenv
```

Then run:

```bash
pip install -r voice_agent/app/backend/requirements.txt
```

#### Step 3: Create & underestand the Evaluation Script

Create a new file at `voice_agent/app/backend/tests/test_flight_agent_evaluation.py` with the following content:

<details>
<summary>Click to expand/collapse</summary>

```python
import os
from azure.ai.evaluation import (
    GroundednessEvaluator, 
    CoherenceEvaluator, 
    RelevanceEvaluator,
    IntentResolutionEvaluator,
    ToolCallAccuracyEvaluator,
    TaskAdherenceEvaluator
)
from dotenv import load_dotenv
load_dotenv()

# Load environment variables
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
model = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")

# Model config for evaluators
model_config = {
    "azure_deployment": model,  # or your preferred model
    "azure_endpoint": endpoint,
    "api_key": api_key
}

# Flight agent tool definitions for ToolCallAccuracyEvaluator
flight_agent_tool_definitions = [
    {
        "name": "search_airline_knowledgebase",
        "description": "Searches the airline knowledge base to answer airline policy questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "The search query to use to search the knowledge base."
                }
            },
            "required": ["search_query"]
        }
    },
    {
        "name": "query_flights",
        "description": "Query the list of available flights for a given departure airport code, arrival airport code and departure time.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_": {
                    "type": "string",
                    "description": "The departure airport code."
                },
                "to": {
                    "type": "string",
                    "description": "The arrival airport code."
                },
                "departure_time": {
                    "type": "string",
                    "description": "The departure time."
                }
            },
            "required": ["from_", "to", "departure_time"]
        }
    },
    {
        "name": "check_flight_status",
        "description": "Checks the flight status for a flight.",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_num": {
                    "type": "string",
                    "description": "The flight number."
                },
                "from_": {
                    "type": "string",
                    "description": "The departure airport code."
                }
            },
            "required": ["flight_num", "from_"]
        }
    },
    {
        "name": "confirm_flight_change",
        "description": "Execute the flight change after confirming with the customer.",
        "parameters": {
            "type": "object",
            "properties": {
                "current_ticket_number": {
                    "type": "string",
                    "description": "The current ticket number."
                },
                "new_flight_number": {
                    "type": "string",
                    "description": "The new flight number."
                },
                "new_departure_time": {
                    "type": "string",
                    "description": "The new departure time."
                },
                "new_arrival_time": {
                    "type": "string",
                    "description": "The new arrival time."
                }
            },
            "required": ["current_ticket_number", "new_flight_number", "new_departure_time", "new_arrival_time"]
        }
    },
    {
        "name": "check_change_booking",
        "description": "Check the feasibility and outcome of a presumed flight change.",
        "parameters": {
            "type": "object",
            "properties": {
                "current_ticket_number": {
                    "type": "string",
                    "description": "The current ticket number."
                },
                "current_flight_number": {
                    "type": "string",
                    "description": "The current flight number."
                },
                "new_flight_number": {
                    "type": "string",
                    "description": "The new flight number."
                },
                "from_": {
                    "type": "string",
                    "description": "The departure airport code."
                }
            },
            "required": ["current_ticket_number", "current_flight_number", "new_flight_number", "from_"]
        }
    },
    {
        "name": "load_user_flight_info",
        "description": "Loads the flight information for a user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user id."
                }
            },
            "required": ["user_id"]
        }
    }
]

# Example test cases for the flight agent with tool calls
test_cases = [
    {
        "input": "I want to book a flight from New York to London on May 10th",
        "output": "I'd be happy to help you book a flight from New York to London on May 10th. Let me search for available flights for you.",
        "tool_calls": [
            {
                "type": "tool_call",
                "tool_call_id": "call_123",
                "name": "query_flights",
                "arguments": {
                    "from_": "NYC",
                    "to": "LHR",
                    "departure_time": "2025-05-10T12:00:00"
                }
            }
        ],
        "expected_intent": "flight booking",
        "context": "There are several flights available from New York to London on May 10th, 2025. The options include morning, afternoon, and evening departures with various airlines."
    },
    {
        "input": "What is the baggage allowance for economy class?",
        "output": "Let me check the baggage policy for economy class flights for you.",
        "tool_calls": [
            {
                "type": "tool_call",
                "tool_call_id": "call_456",
                "name": "search_airline_knowledgebase",
                "arguments": {
                    "search_query": "baggage allowance economy class"
                }
            }
        ],
        "context": "The baggage allowance for economy class is one checked bag up to 23kg and one carry-on.",
        "expected_intent": "policy inquiry"
    },
    {
        "input": "I need to change my flight AA123 from JFK. My ticket number is 1234567890.",
        "output": "I understand you want to change your flight AA123 departing from JFK. Let me check what options are available for you.",
        "tool_calls": [
            {
                "type": "tool_call",
                "tool_call_id": "call_789",
                "name": "check_change_booking",
                "arguments": {
                    "current_ticket_number": "1234567890",
                    "current_flight_number": "AA123",
                    "new_flight_number": "AA456",
                    "from_": "JFK"
                }
            }
        ],
        "expected_intent": "flight change",
        "context": "Flight AA123 from JFK is scheduled for April 30, 2025. There are alternative flights available on May 1st and May 2nd with similar schedules."
    },
    {
        "input": "Can you check the status of flight AA490 from Los Angeles?",
        "output": "I'd be happy to check the status of flight AA490 from Los Angeles for you.",
        "tool_calls": [
            {
                "type": "tool_call",
                "tool_call_id": "call_012",
                "name": "check_flight_status",
                "arguments": {
                    "flight_num": "AA490",
                    "from_": "LAX"
                }
            }
        ],
        "expected_intent": "flight status",
        "context": "Flight AA490 from Los Angeles is currently on time and scheduled to depart at 2:30 PM local time."
    }
]

# Initialize all evaluators
metrics = {
    "Groundedness": GroundednessEvaluator(model_config=model_config),
    "Coherence": CoherenceEvaluator(model_config=model_config),
    "Relevance": RelevanceEvaluator(model_config=model_config),
    "IntentResolution": IntentResolutionEvaluator(model_config=model_config),
    "ToolCallAccuracy": ToolCallAccuracyEvaluator(model_config=model_config),
    "TaskAdherence": TaskAdherenceEvaluator(model_config=model_config)
}

print("=== Flight Agent Evaluation Results ===")

# Run evaluation for each test case
for idx, case in enumerate(test_cases, 1):
    print(f"\n*****Test Case {idx}: {case['input']}")
    for metric_name, evaluator in metrics.items():
        score = None
        try:
            if metric_name == "Groundedness":
                if "context" in case:
                    score = evaluator(
                        context=case["context"],
                        response=case["output"]
                    )
                else:
                    print(f"\n   {metric_name}: Skipped (missing context in test case)")
                    continue
            elif metric_name == "Coherence":
                # Based on documentation, Coherence evaluator expects query and response parameters
                score = evaluator(
                    query=case["input"],
                    response=case["output"]
                )
            elif metric_name == "Relevance":
                # Based on documentation, Relevance evaluator expects query and response parameters
                score = evaluator(
                    query=case["input"],
                    response=case["output"]
                )
            elif metric_name == "IntentResolution":
                # For Intent Resolution, we need the expected intent
                score = evaluator(
                    query=case["input"],
                    response=case["output"],
                    tool_definitions=flight_agent_tool_definitions
                )
                print(f"\n   {metric_name}: {score} (Expected: {case.get('expected_intent', 'unknown')})")
                continue
            elif metric_name == "ToolCallAccuracy":
                # For Tool Call Accuracy, we need the tool calls and tool definitions
                if "tool_calls" in case:
                    score = evaluator(
                        query=case["input"],
                        tool_calls=case["tool_calls"],
                        tool_definitions=flight_agent_tool_definitions
                    )
                else:
                    print(f"\n   {metric_name}: Skipped (missing tool_calls in test case)")
                    continue
            elif metric_name == "TaskAdherence":
                # For Task Adherence, evaluate how well the response adheres to the flight agent's task
                score = evaluator(
                    query=case["input"],
                    response=case["output"],
                    tool_calls=case.get("tool_calls")
                )

            print(f"\n   {metric_name}: {score}")
        except Exception as e:
            print(f"\n   Error evaluating {metric_name}: {e}")


# Print overall results summary
print("\n=== Overall Evaluation Summary ===")
print("This summary would show aggregated metrics across all test cases.")
print("For a production environment, you would typically run these evaluations")
print("against a larger dataset and track metrics over time.")
```
</details>


Let's break down the key components of this evaluation script:

1. **Tool Definitions**: This section defines all available tools for the flight agent in a format that the evaluation SDK can understand.

2. **Test Cases**: These are pre-defined scenarios that represent common customer interactions with the flight agent.

3. **Evaluators**:
   - **Groundedness**: Measures if responses are factually accurate based on given context
   - **Coherence**: Measures if responses make logical sense
   - **Relevance**: Measures if responses are relevant to the user query
   - **IntentResolution**: Measures if the agent correctly identifies user intent
   - **ToolCallAccuracy**: Measures if the agent uses the right tools with the right parameters
   - **TaskAdherence**: Measures if the agent stays on task

#### Step 4: Run the Evaluation

Execute the script to evaluate your flight agent:

```bash
cd voice_agent/app/backend
python -m tests.test_flight_agent_evaluation
```

The output will display scores for each evaluator across all test cases.

#### Step 5: Analyze the Results

After running the evaluation, you'll see scores for each metric. These scores help you:

1. Identify areas where the agent performs well
2. Pinpoint specific scenarios where the agent struggles
3. Compare performance before and after model upgrades

Focus on metrics that score below your expectations and look for patterns in the test cases where the agent performed poorly.

#### Step 6: Upgrade the LLM 

Upgrade the LLM by picking another LLM to evaluate.  Update the file in Step 1 with name of new LLM.

#### Step 7: Rerun the evaluation

Follow Step 4: Run the Evaluation

#### Step 8: Analyze and compare results between the runs

Review Step 5: Analyze the Results

#### Step 9: Iterate and Improve

Based on your findings:

1. Modify the agent's prompts or tool definitions
2. Add more test cases for scenarios that revealed issues
3. Re-run the evaluation to check if changes improved performance

#### What You've Learned

- How to set up and run evaluations using the Azure AI Evaluation SDK
- How different metrics help assess various aspects of agent performance
- How to interpret evaluation results to guide improvements

This approach provides quantitative metrics to measure the impact of upgrading your agent's LLM and helps ensure that changes maintain or improve the user experience.

## Security/Safety Persona 
- Exercise 1: leverage of Evaluation SDK simulators to try to break the system and see if any extra safety needs to be put in place. https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data
- Exercise 2: one agent (new car rental agent) doesn't pass test above, fix it by adding filter -> retest -> PR
- Exercise 3: showcase that agents act using an identity that is tied to the logged in user and not a service principal -> demo that datastore access or service access prevents access to data not in scope of this identity
- (phase-2 / consider once this functionality is integrated into the AI Foundry Agent Service post Build 2025): Exercise 4: real-time monitoring around generative quality & safety (RAI)

---
#### Navigation: [Home](../../README.md) | [Previous Section](../04_deploy/README.md) | [Next Section](../06_observability/README.md)
