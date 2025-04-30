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