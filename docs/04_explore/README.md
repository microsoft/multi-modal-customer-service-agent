# Explore this Solution Accelerator with Guided Exercises

## Overview

Welcome to the hands-on exploration of the Real-time Multi-modal & Multi-domain Agentic Solution Accelerator! This section provides guided exercises designed to help you understand, extend, and optimize this production-grade AI system through practical, real-world scenarios.

### What You'll Learn

Through these exercises, you will gain experience with:

- **Multi-agent Architecture**: Understanding how to design, implement, and orchestrate multiple specialized AI agents
- **Production AI Operations**: Best practices for monitoring, debugging, evaluating, and securing AI systems
- **Azure AI Services Integration**: Hands-on experience with Azure OpenAI, AI Foundry, and related services
- **Real-time Conversational AI**: Building and optimizing voice-enabled, streaming AI applications
- **DevOps for AI**: Implementing CI/CD, monitoring, and maintenance workflows for AI systems
- **AI Safety and Security**: Implementing responsible AI practices and security measures

### Prerequisites

Before starting these exercises, ensure you have completed:

1. **[Architecture Overview](../01_architecture/README.md)** - Understanding of the system design and components
2. **[Environment Setup](../02_setup/README.md)** - Development environment configuration and Azure resources
3. **[Observability](../03_observability/README.md)** - Familiarity with monitoring and tracing tools

**Technical Prerequisites:**
- Python 3.11+ development environment
- VS Code with recommended extensions
- Azure CLI and PowerShell
- Git for version control
- Access to configured Azure OpenAI and related services

### Exercise Structure by Persona

This section is organized around three key personas involved in AI solution development and operations:

#### 🧑‍💻 PM / Developer Persona (Estimated Time: 3-4 hours)
Focus on extending functionality and implementing new features
- **Exercise 1**: Add a new agent (car rental agent) - *90 minutes*
- **Exercise 2**: Debug/fix/commit workflow - *60 minutes*

#### ⚙️ DevOps / SRE Persona (Estimated Time: 2-3 hours)  
Focus on evaluation, monitoring, and performance optimization
- **Exercise 1**: Upgrade LLM and evaluate with Azure AI Evaluation SDK - *90 minutes*
- **Exercise 2**: Performance monitoring and optimization - *60 minutes*

#### 🔒 Security / Safety Persona (Estimated Time: 2-3 hours)
Focus on security, safety, and responsible AI practices
- **Exercise 1**: Adversarial testing and safety evaluation - *90 minutes*
- **Exercise 2**: Identity-based access control - *60 minutes*
- **Exercise 3**: Real-time monitoring and remediation - *60 minutes*

### Table of Contents

- [PM / Developer Persona](#pm--developer-persona)
  - [Exercise 1: Add a New Agent (Car Rental Agent)](#exercise-1-add-a-new-agent-car-rental-agent)
  - [Exercise 2: Debug/Fix/Commit Flow](#exercise-2-debugfixcommit-flow)
- [DevOps / SRE Persona](#devops--sre-persona)
  - [Exercise 1: Upgrade LLM and Evaluate](#exercise-1-upgrade-llm-and-evaluate)
  - [Exercise 2: Performance Monitoring](#exercise-2-performance-monitoring)
- [Security / Safety Persona](#security--safety-persona)
  - [Exercise 1: Adversarial Testing](#exercise-1-adversarial-testing)
  - [Exercise 2: Identity-Based Access Control](#exercise-2-identity-based-access-control)
  - [Exercise 3: Real-time Monitoring](#exercise-3-real-time-monitoring)

### How to Use These Exercises

1. **Choose Your Path**: Select exercises based on your role and interests
2. **Follow Prerequisites**: Ensure you have the required background and setup
3. **Work Step-by-Step**: Each exercise builds on previous knowledge
4. **Validate Progress**: Use the provided checkpoints to verify your work
5. **Experiment**: Try variations and explore beyond the basic requirements

---

## PM / Developer Persona

### Exercise 1: Add a New Agent (Car Rental Agent)

#### Learning Objectives
By completing this exercise, you will learn how to:
- Extend the multi-agent architecture by adding a new specialized agent
- Implement agent tools and plugins using Semantic Kernel
- Configure agent profiles and personas
- Integrate semantic search capabilities with Azure OpenAI embeddings
- Test and validate new agent functionality

#### Prerequisites
- Completed [Environment Setup](../02_setup/README.md)
- Basic understanding of Python and async programming
- Familiarity with Azure OpenAI services
- Understanding of the project's multi-agent architecture

#### Estimated Time
90 minutes

#### Overview
In this exercise, you'll extend the existing multi-agent customer service system by adding a new car rental agent. This will demonstrate the scalability and extensibility of the architecture, showing how new business domains can be added without disrupting existing functionality.

#### What You'll Build
- A complete car rental agent with booking and policy search capabilities
- Integration with the existing intent detection system
- Semantic search functionality for rental policies
- Proper error handling and validation

#### Understanding Multi-Agent Architecture

Before we begin building, let's understand how the multi-agent system works and where our new car rental agent fits:

##### 🏗️ Architecture Overview
The system uses a **Router-Agent pattern** with specialized domain agents:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Router Agent  │    │  Flight Agent   │    │  Hotel Agent    │
│ (Intent Detection)  │    │ (Flights & Status) │    │ (Reservations)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐             │
         └──────────────│ Car Rental Agent │─────────────┘
                        │   (NEW!)        │
                        └─────────────────┘
```

##### 🔄 Agent Interaction Flow
1. **User Input** → Router Agent analyzes intent
2. **Intent Detection** → Determines which specialized agent to use
3. **Agent Selection** → Routes to appropriate domain agent (Flight, Hotel, or Car Rental)
4. **Tool Execution** → Agent uses its specialized tools to fulfill the request
5. **Response** → Agent returns formatted response to user

##### 💡 Why This Pattern?
- **Separation of Concerns**: Each agent handles one business domain
- **Scalability**: Easy to add new domains without affecting existing ones
- **Maintainability**: Domain-specific logic is isolated and easier to update
- **Flexibility**: Can easily modify or replace individual agents

##### 🧩 Components We'll Build
1. **Agent Tools** (`car_rental_plugins.py`) - The functions the agent can call
2. **Agent Profile** (`car_rental_agent_profile.yaml`) - The agent's persona and behavior
3. **System Integration** - Connecting the agent to the router and intent detection
4. **Knowledge Base** - Semantic search for rental policies using embeddings

#### Step 1: Create the Car Rental Tools Plugin

Now let's build the tools that give our car rental agent its capabilities.

**🎯 What This Step Accomplishes:**
- Defines the functions (tools) our agent can use
- Implements mock car rental operations
- Sets up the foundation for semantic search

Create a new file `car_rental_plugins.py` in `voice_agent\app\backend\agents\tools\` and add the following code:

**File Path:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\agents\tools\car_rental_plugins.py`

##### 🔧 Understanding Semantic Kernel Functions

Before we write the code, let's understand what we're building:

- **`@kernel_function`**: This decorator tells Semantic Kernel that this function can be called by the LLM
- **`description`**: Helps the LLM understand when to use this function
- **`name`**: The function name the LLM will reference
- **Async functions**: All agent tools are asynchronous for better performance

<details>
<summary>🔽 Click to expand car_rental_plugins.py - Part 1: Basic Setup</summary>

```python
from typing import List
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function

class Car_Rental_Tools:
    """Tools for car rental agent to perform various rental operations"""
```

**📝 What this does:**
- Imports required Semantic Kernel components
- Creates the main tools class that will contain all car rental functions
- The docstring helps document the purpose of this class

</details>

<details>
<summary>🔽 Click to expand car_rental_plugins.py - Part 2: Car Search Function</summary>

```python
    @kernel_function(
        description="Search for available rental cars based on location and dates",
        name="search_cars"
    )
    async def search_cars(self, location: str, pickup_date: str, return_date: str) -> str:
        """
        Search for available rental cars at a specific location and date range.
        
        Args:
            location: The pickup location (e.g., "New York", "LAX Airport")
            pickup_date: The rental start date (e.g., "2025-07-15")
            return_date: The rental end date (e.g., "2025-07-20")
            
        Returns:
            Formatted string with available car options
        """
        # Mock implementation - in production, this would call a real car rental API
        return f"Found available cars in {location} from {pickup_date} to {return_date}: \n" \
                "1. Economy - Toyota Corolla ($45/day)\n" \
                "2. SUV - Honda CR-V ($65/day)\n" \
                "3. Luxury - BMW 5 Series ($95/day)"
```

**📝 What this does:**
- Provides car search functionality based on location and dates
- Returns formatted results that the LLM can present to users
- Uses mock data for demonstration (you'd replace with real API calls)

</details>

<details>
<summary>🔽 Click to expand car_rental_plugins.py - Part 3: Car Details Function</summary>

```python
    @kernel_function(
        description="Get detailed information about a specific rental car",
        name="get_car_details"
    )
    async def get_car_details(self, car_id: str) -> str:
        """
        Get detailed specifications and features for a specific car.
        
        Args:
            car_id: The ID of the car to get details for (e.g., "1", "2", "3")
            
        Returns:
            Detailed car specifications and features
        """
        # Mock car database - in production, this would query a real database
        car_details = {
            "1": "Toyota Corolla: 4 doors, 5 seats, automatic transmission, GPS, bluetooth",
            "2": "Honda CR-V: 5 doors, 5 seats, automatic transmission, GPS, bluetooth, roof rack",
            "3": "BMW 5 Series: 4 doors, 5 seats, automatic transmission, GPS, bluetooth, leather seats"
        }
        return car_details.get(car_id, "Car not found - please check the car ID")
```
</details>

**📝 What this does:**
- Provides detailed information about specific vehicles
- Uses a simple lookup system for mock data
- Includes error handling for invalid car IDs

**✅ Validation Checklist:**
- [ ] File created in correct directory: `voice_agent\app\backend\agents\tools\`
- [ ] All imports are correct and no syntax errors
- [ ] Functions are properly decorated with `@kernel_function`
- [ ] Function descriptions clearly explain their purpose
- [ ] Mock data returns realistic car rental information

**🔧 Troubleshooting Common Issues:**
- **Import Error**: Ensure Semantic Kernel is installed: `pip install semantic-kernel`
- **Directory Not Found**: Create the directory structure if it doesn't exist
- **Syntax Errors**: Check Python indentation and parentheses matching
- **Function Not Found**: Verify the `@kernel_function` decorator is applied correctly

**🧪 Test Your Work:**
Try creating a simple test script to verify your functions work:
```python
# Test script (optional)
from car_rental_plugins import Car_Rental_Tools
import asyncio

async def test_functions():
    tools = Car_Rental_Tools()
    cars = await tools.search_cars("New York", "2025-07-15", "2025-07-20")
    print("Search Results:", cars)
    
    details = await tools.get_car_details("1")
    print("Car Details:", details)

# asyncio.run(test_functions())  # Uncomment to run test
```

#### Step 2: Create the Car Rental Agent Profile

**🎯 What This Step Accomplishes:**
- Defines the agent's personality and behavior
- Sets up the conversational persona for car rental interactions
- Configures how the agent should respond to different situations

##### 🤖 Understanding Agent Profiles

Agent profiles in this system define:
- **Persona**: How the agent should behave and communicate
- **Context Variables**: Dynamic information like customer name and ID
- **Responsibilities**: What the agent should and shouldn't do
- **Tone**: Professional, helpful, courteous communication style

#### Step 2: Create the Car Rental Agent Profile

Create the agent configuration file that defines the car rental agent's persona and behavior.

**File Path:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\agents\agent_profiles\car_rental_agent_profile.yaml`
<details>
<summary>🔽 Click to expand car_rental_agent_profile.yaml code</summary>

```yaml  
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

**✅ Validation:** Confirm the YAML file is properly formatted and saved in the agent_profiles directory.

#### Step 3: Integrate the Agent into the System

Update the RTMiddleTier class to recognize and load the new car rental agent.

**File to Modify:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\rtmt.py`

Add the import statement at the top of the file:

<details>
<summary>🔽 Click to expand import and _load_agents method changes</summary>

**Add import at the top of the file:**
```python
from agents.tools.car_rental_plugins import Car_Rental_Tools
```

**Update the `_load_agents` method:**
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

**✅ Validation:** Check that the import works and the agent loads without errors when starting the application.

#### Step 4: Update Intent Detection

Configure the system to recognize car rental-related queries and route them to the new agent.

**File to Modify:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\utility.py`

Update the `detect_intent` method to include the car rental agent in the system message:    
<details>
    <summary>🔽 Click to expand intent detection update</summary>

**Update message parameter to include:**

```python
    - **car_rental_agent**: Deal with car rentals, vehicle reservations, changes, and general car rental policy questions.
```
</details>

> **📝 Note:** The intent detection model has already been updated to recognize car rental-related queries. See the `intent_detection_model` directory for training data and model details.

**✅ Validation:** Test that car rental queries (e.g., "I need to rent a car") are properly routed to the car rental agent.

#### Step 5: Add Semantic Search for Rental Policies

**🎯 What This Step Accomplishes:**
- Implements intelligent policy search using AI embeddings
- Enables the agent to answer complex policy questions
- Demonstrates advanced RAG (Retrieval Augmented Generation) patterns

##### 🧠 Understanding Embeddings and Semantic Search

Before we implement the search functionality, let's understand the concepts:

**What are Embeddings?**
- Embeddings are vector representations of text that capture semantic meaning
- Similar concepts have similar embeddings (even with different words)
- Example: "car insurance" and "vehicle coverage" would have similar embeddings

**How Semantic Search Works:**
```
1. User Question: "What's covered in basic insurance?"
   ↓
2. Convert question to embedding vector
   ↓
3. Compare with all policy embeddings using cosine similarity
   ↓
4. Return most relevant policy documents
   ↓
5. LLM uses retrieved policies to answer the question
```

**Why This is Powerful:**
- Understands intent, not just keywords
- Works across different phrasings of the same question
- Scales to large knowledge bases

Implement knowledge base search capabilities using Azure OpenAI embeddings for car rental policies.

##### Step 5a: Create the Rental Policy Knowledge Base

Create a structured JSON file containing car rental policy information that will be searchable.

**🗂️ Knowledge Base Structure:**
- Each policy has an ID, human-readable text, and space for embeddings
- The `policy_text_embedding` field will store the vector representation
- Initially set to `null` - we'll generate these in a later step

**File Path:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\data\car_rental_policy.json`
<details>
    <summary>🔽 Click to expand car_rental_policy.json content</summary>

```json
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

**✅ Validation:** Verify the JSON file is valid and saved in the correct data directory.

##### Step 5b: Update the Plugin with Search Capabilities

Enhance the car rental plugin with Azure OpenAI embedding search functionality.

**File to Modify:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\agents\tools\car_rental_plugins.py`

Add the required imports and search functionality:
<details>
    <summary>🔽 Click to expand imports & search content</summary>

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
        
            return "\n".join(f"{chunk_id}\n{content}" for chunk_id, content, _ in cosine_list)      # Initialize the search client
    search_client = SearchClient("./data/car_rental_policy.json")
 ```
 </details>

##### Step 5c: Add Policy Search Function to Plugin

Update the Car_Rental_Tools class to include the policy search capability.

Add the required imports and search function to the plugin:

<details>
    <summary>🔽 Click to expand additional imports and search function</summary>

**Add these imports at the top of the file:**
```python
    from openai import AzureOpenAI
    import json
    from scipy import spatial
```

**Add this function to the Car_Rental_Tools class:**
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

**✅ Validation:** Test the policy search function by querying for rental policies.

##### Step 5d: Create Embedding Generation Script

**🎯 What This Script Does:**
- Reads the policy JSON file we created
- Calls Azure OpenAI to generate embeddings for each policy
- Saves the embeddings back to the JSON file
- Prepares the data for semantic search

**🔧 How Embedding Generation Works:**
1. **Load Policy Text** → Read human-readable policy descriptions
2. **Call Azure OpenAI** → Convert text to 1536-dimensional vectors
3. **Store Embeddings** → Save vectors alongside original text
4. **Enable Search** → Embeddings allow semantic similarity comparisons

Create a script to generate embeddings for the rental policy data.

**File Path:** `c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend\scripts\generate_car_rental_policy_embeddings.py`

<details>
<summary>🔽 Click to expand embedding generation script</summary>

```python
import json
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def generate_embeddings(input_file: str):
    """
    Generate embeddings for policy documents using Azure OpenAI.
    
    This function:
    1. Reads policy data from JSON file
    2. Generates embeddings for each policy text
    3. Saves embeddings back to the same file
    
    Args:
        input_file: Path to the JSON file containing policy data
    """
    # Initialize Azure OpenAI client for embeddings
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_EMB_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_EMB_ENDPOINT"),
        api_version="2023-12-01-preview"
    )

    print(f"Loading policy data from {input_file}...")
    # Load the JSON file
    with open(input_file, 'r') as file:
        data = json.load(file)

    print(f"Generating embeddings for {len(data)} policy documents...")
    # Generate embeddings for each policy text
    for item in data:
        print(f"Processing policy: {item['id']}")
        response = client.embeddings.create(
            input=[item['policy_text']],
            model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
        )
        # Store the embedding vector (list of 1536 floating point numbers)
        item['policy_text_embedding'] = response.data[0].embedding

    print(f"Saving embeddings back to {input_file}...")
    # Save the updated JSON with embeddings
    output_file = input_file
    with open(output_file, 'w') as file:
        json.dump(data, file, indent=2)
    
    print("✅ Embedding generation complete!")

if __name__ == "__main__":
    generate_embeddings("./data/car_rental_policy.json")
```
</details>

**📝 Important Notes:**
- **Environment Variables**: Ensure your `.env` file has the embedding API credentials
- **Processing Time**: Embedding generation may take a few seconds per document
- **API Costs**: Each embedding call uses Azure OpenAI tokens
- **File Size**: The JSON file will grow significantly after adding embeddings

**✅ Validation:** Verify the script file is created in the correct scripts directory.

##### Step 5e: Generate Embeddings

Run the embedding generation script to create the policy embeddings.

**Command to Run:**    
```powershell
    cd c:\Code\multi-modal-customer-service-agent\voice_agent\app\backend
    python scripts/generate_car_rental_policy_embeddings.py
```

**✅ Validation:** Check that the `car_rental_policy.json` file now contains embedding vectors for each policy entry.

##### Step 5f: Test the Car Rental Agent

Test the complete car rental agent functionality with various queries.

**Test Queries to Try:**
- Insurance coverage options and costs
- Rental requirements and age restrictions  
- Deductibles and additional coverage options
- Car availability and booking queries

**✅ Validation:** Verify that the agent can successfully:
- Search for available cars
- Provide car details
- Answer policy questions using semantic search
- Route car rental queries correctly

#### Exercise Summary: What You've Accomplished

Congratulations! You have successfully:

✅ **Extended the multi-agent architecture** by adding a complete car rental domain  
✅ **Implemented agent tools** using Semantic Kernel with proper async functions  
✅ **Configured agent profiles** with persona and behavioral guidelines  
✅ **Added semantic search capabilities** using Azure OpenAI embeddings  
✅ **Integrated intent detection** to route car rental queries appropriately  
✅ **Tested end-to-end functionality** with real queries and validation

#### Complete Car Rental Plugin Reference

For reference, here's the complete `car_rental_plugins.py` file:

<details>
<summary>🔽 Click to see the Complete Car Rental Plugin Reference</summary>

```python
from typing import List
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
import os
import json
from scipy import spatial
from openai import AzureOpenAI

class Car_Rental_Tools:
    """Tools for car rental agent to perform various rental operations"""

    @kernel_function(
        description="Search for available rental cars based on location and dates",
        name="search_cars"
    )
    async def search_cars(self, location: str, pickup_date: str, return_date: str) -> str:
        """
        Search for available rental cars at a specific location and date range.
        
        Args:
            location: The pickup location (e.g., "New York", "LAX Airport")
            pickup_date: The rental start date (e.g., "2025-07-15")
            return_date: The rental end date (e.g., "2025-07-20")
            
        Returns:
            Formatted string with available car options
        """
        # Mock implementation - in production, this would call a real car rental API
        return f"Found available cars in {location} from {pickup_date} to {return_date}: \n" \
                "1. Economy - Toyota Corolla ($45/day)\n" \
                "2. SUV - Honda CR-V ($65/day)\n" \
                "3. Luxury - BMW 5 Series ($95/day)"

    @kernel_function(
        description="Get detailed information about a specific rental car",
        name="get_car_details"
    )
    async def get_car_details(self, car_id: str) -> str:
        """
        Get detailed specifications and features for a specific car.
        
        Args:
            car_id: The ID of the car to get details for (e.g., "1", "2", "3")
            
        Returns:
            Detailed car specifications and features
        """
        # Mock car database - in production, this would query a real database
        car_details = {
            "1": "Toyota Corolla: 4 doors, 5 seats, automatic transmission, GPS, bluetooth",
            "2": "Honda CR-V: 5 doors, 5 seats, automatic transmission, GPS, bluetooth, roof rack",
            "3": "BMW 5 Series: 4 doors, 5 seats, automatic transmission, GPS, bluetooth, leather seats"
        }
        return car_details.get(car_id, "Car not found - please check the car ID")

    @kernel_function(
        description="Search car rental policies using semantic search.",
        name="search_rental_policy"
    )
    async def search_rental_policy(self, question: str) -> str:
        """
        Search the car rental policy knowledge base for relevant information.
        
        Args:
            question: The user's policy-related question
            
        Returns:
            Relevant policy text(s) from the knowledge base
        """
        return search_client.find_article(question)

# Azure OpenAI embedding environment variables
AZURE_OPENAI_EMB_API_KEY = os.getenv("AZURE_OPENAI_EMB_API_KEY")
AZURE_OPENAI_EMB_ENDPOINT = os.getenv("AZURE_OPENAI_EMB_ENDPOINT")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "text-embedding-ada-002")

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
            for item in self.chunks_emb if item['policy_text_embedding'] is not None
        ]
        cosine_list.sort(key=lambda x: x[2], reverse=True)
        cosine_list = cosine_list[:topk]
        return "\n".join(f"{chunk_id}\n{content}" for chunk_id, content, _ in cosine_list)

# Initialize the search client
search_client = SearchClient(os.path.join(os.path.dirname(__file__), '../../data/car_rental_policy.json'))

```
</details>

### Exercise 2: Debug/Fix/Commit Workflow

#### Learning Objectives
By completing this exercise, you will learn how to:
- Identify and diagnose performance issues in multi-agent systems
- Use observability tools (tracing in AI Foundry) to troubleshoot problems
- Implement fixes for system-level issues
- Apply proper Git workflow for AI system changes
- Run evaluation tests to validate fixes

#### Prerequisites
- Completed Exercise 1 (Car Rental Agent)
- Familiarity with [Observability tools](../03_observability/README.md)
- Basic Git knowledge
- Understanding of Azure AI Foundry tracing

#### Estimated Time
60 minutes

#### Overview
This exercise simulates a real-world debugging scenario where you'll encounter a performance issue, diagnose it using observability tools, implement a fix, and validate the solution through testing.

#### Scenario Description
You'll work with an artificial performance problem in the multi-agent system and follow a complete debugging and remediation workflow.

**What You'll Do:**
1. Identify a scenario that 'fails' from a functionality standpoint
2. Use observability (tracing in AI Foundry) to diagnose the problem
3. Implement fixes (system prompts, configuration, etc.)
4. Run local evaluation tests to validate the fix
5. Create a proper Pull Request with your changes

**✅ Success Criteria:**
- Successfully identify the root cause using tracing tools
- Implement a working fix
- Pass all evaluation tests
- Create proper documentation for the fix

## DevOps / SRE Persona

### Exercise 1: Upgrade LLM and Evaluate with Azure AI Evaluation SDK

#### Learning Objectives
By completing this exercise, you will learn how to:
- Implement systematic LLM evaluation using industry-standard metrics
- Use the Azure AI Evaluation SDK to assess AI agent performance
- Compare different models quantitatively to make data-driven decisions
- Establish performance baselines for AI systems
- Track performance improvements over time
- Apply best practices for model upgrades in production

#### Prerequisites
- Completed [Environment Setup](../02_setup/README.md)
- Basic understanding of Python and VS Code
- Access to Azure OpenAI resources
- Familiarity with AI evaluation concepts
- Understanding of the flight agent implementation

#### Estimated Time
90 minutes

#### Why LLM Evaluation Matters

Before we dive into the technical implementation, let's understand why rigorous model evaluation is critical in production AI systems:

##### 🔍 The Importance of Systematic Evaluation
LLM-powered agents can be unpredictable, and changes that seem minor can have significant impacts on:

- **Functional Correctness**: Does the agent perform required tasks accurately?
- **Reliability**: Does the agent behave consistently across similar inputs?
- **Safety**: Does the agent avoid harmful or incorrect outputs?
- **Efficiency**: Does the agent complete tasks with minimal interactions?

##### 📊 Key Evaluation Metrics Explained

When evaluating AI agents, different metrics reveal different aspects of performance:

| Metric | What It Measures | Why It Matters | Ideal Score |
|--------|------------------|----------------|-------------|
| **Groundedness** | How factually accurate responses are based on provided context | Prevents hallucinations and misinformation | 1.0 (high) |
| **Coherence** | How logical and well-structured responses are | Ensures clear communication | 1.0 (high) |
| **Relevance** | How well responses address the user's query | Prevents off-topic responses | 1.0 (high) |
| **Intent Resolution** | Accuracy in identifying the user's intent | Ensures correct understanding of requests | 1.0 (high) |
| **Tool Call Accuracy** | Correct tool selection and parameter passing | Prevents errors in automated actions | 1.0 (high) |
| **Task Adherence** | Staying focused on the required task | Prevents scope creep and distractions | 1.0 (high) |

##### 📈 Performance Tracking Approach

To effectively monitor LLM performance over time:

1. **Establish baseline** with current model
2. **Track deltas** when making changes (model, prompts, etc.)
3. **Maintain a test suite** covering diverse scenarios
4. **Log results** historically to identify trends or regressions

#### Steps Overview

1. Review current LLM configuration 
2. Install required evaluation packages
3. Create & understand the evaluation framework
4. Run baseline evaluation
5. Analyze baseline results
6. Upgrade the LLM
7. Run comparative evaluation
8. Analyze performance improvements
9. Document findings and recommendations

#### Step 1: Review Current LLM Configuration

First, let's examine the current model configuration to understand our starting point.

**🎯 What This Step Accomplishes:**
- Identifies the currently deployed model
- Establishes the configuration we'll be comparing against
- Ensures we're testing the correct deployment

Review the current LLM environment variable in the `.env` file in the backend directory:

```
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
```

This variable tells us which Azure OpenAI model deployment is currently being used by the flight agent. In this case, it's using `gpt-4o-mini`, which is a smaller, faster version of GPT-4o.

**📝 Key Model Characteristics:**
- **GPT-4o-mini**: Optimized for speed and cost with reasonable quality
- **Strengths**: Fast responses, lower cost, good for common queries
- **Limitations**: May struggle with complex reasoning or edge cases

**✅ Validation Checklist:**
- [ ] Confirmed current model deployment name
- [ ] Noted model version for reference
- [ ] Checked if model supports all required capabilities (tool use, etc.)

#### Step 2: Install Required Evaluation Packages

The Azure AI Evaluation SDK provides comprehensive tools for assessing model performance.

**🎯 What This Step Accomplishes:**
- Sets up the required dependencies for evaluation
- Ensures consistent evaluation across different runs
- Prepares the environment for testing multiple models

Install the Azure AI Evaluation SDK:

```bash
pip install azure-ai-evaluation python-dotenv
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

**📋 What We're Installing:**
- **azure-ai-evaluation**: Microsoft's SDK for evaluating LLM performance
- **python-dotenv**: For loading environment variables from .env files

**✅ Validation Checklist:**
- [ ] Packages installed successfully
- [ ] No version conflicts or dependency issues
- [ ] Environment ready for evaluation tasks

#### Step 3: Create the Evaluation Framework

Now we'll create a comprehensive evaluation script that tests the flight agent's performance across multiple dimensions and scenarios.

**🎯 What This Step Accomplishes:**
- Defines relevant test cases that exercise the agent's capabilities
- Configures multiple evaluation metrics
- Creates a reusable framework for ongoing evaluations

Create a new file at `voice_agent/app/backend/tests/test_flight_agent_evaluation.py`.

##### Core Components of the Evaluation Framework

<details>
<summary>🔽 Click to expand Part 1: Imports and Configuration</summary>

```python
import os
import json
from datetime import datetime
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
    "azure_deployment": model,  # The current model deployment
    "azure_endpoint": endpoint,
    "api_key": api_key
}

# Create a unique run ID for tracking this evaluation session
run_id = f"{model}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
```

**📝 What This Does:**
- Imports required evaluation metrics from Azure AI Evaluation SDK
- Loads environment variables for Azure OpenAI access
- Creates a configuration for the evaluator models
- Sets up a unique run ID to track evaluation results over time

</details>

<details>
<summary>🔽 Click to expand Part 2: Tool Definitions</summary>

```python
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
```

**📝 What This Does:**
- Defines all available tools for the flight agent
- Specifies each tool's parameters and requirements
- Mirrors the actual tools available to the flight agent
- Enables the ToolCallAccuracy evaluator to check proper tool usage

</details>

<details>
<summary>🔽 Click to expand Part 3: Test Cases</summary>

```python
# Example test cases for the flight agent with tool calls
test_cases = [
    {
        "id": "booking-1",
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
        "id": "policy-1",
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
        "id": "change-1",
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
        "id": "status-1",
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
    },
    {
        "id": "user-info-1",
        "input": "What flights do I have booked?",
        "output": "I'd be happy to check your booked flights. Let me pull up your flight information.",
        "tool_calls": [
            {
                "type": "tool_call",
                "tool_call_id": "call_345",
                "name": "load_user_flight_info",
                "arguments": {
                    "user_id": "current_user"
                }
            }
        ],
        "expected_intent": "booking information",
        "context": "The user has two upcoming flights: AA789 from NYC to LAX on June 30, 2025, and BA456 from LAX to LHR on July 5, 2025."
    }
]
```

**📝 What This Does:**
- Defines test scenarios that cover different user intents
- Includes expected outputs and tool calls for each scenario
- Provides context information for groundedness evaluation
- Creates a comprehensive test suite for agent evaluation

**Test Case Anatomy:**
- **id**: Unique identifier for the test case
- **input**: The user query
- **output**: Expected agent response 
- **tool_calls**: Expected tools the agent should use
- **expected_intent**: The intent the agent should identify
- **context**: Background information to evaluate factual accuracy

</details>

<details>
<summary>🔽 Click to expand Part 4: Evaluation Logic</summary>

```python
# Initialize all evaluators
metrics = {
    "Groundedness": GroundednessEvaluator(model_config=model_config),
    "Coherence": CoherenceEvaluator(model_config=model_config),
    "Relevance": RelevanceEvaluator(model_config=model_config),
    "IntentResolution": IntentResolutionEvaluator(model_config=model_config),
    "ToolCallAccuracy": ToolCallAccuracyEvaluator(model_config=model_config),
    "TaskAdherence": TaskAdherenceEvaluator(model_config=model_config)
}

# Results storage
results = {
    "run_id": run_id,
    "model": model,
    "timestamp": datetime.now().isoformat(),
    "test_cases": {}
}

print(f"=== Flight Agent Evaluation Results (Model: {model}) ===")

# Run evaluation for each test case
for idx, case in enumerate(test_cases, 1):
    case_id = case.get("id", f"case-{idx}")
    print(f"\n***** Test Case {idx}: {case['input']}")
    
    case_results = {
        "input": case["input"],
        "metrics": {}
    }
    
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
                    print(f"\n   {metric_name}: Skipped (missing context)")
                    continue
            elif metric_name == "Coherence":
                score = evaluator(
                    query=case["input"],
                    response=case["output"]
                )
            elif metric_name == "Relevance":
                score = evaluator(
                    query=case["input"],
                    response=case["output"]
                )
            elif metric_name == "IntentResolution":
                score = evaluator(
                    query=case["input"],
                    response=case["output"],
                    tool_definitions=flight_agent_tool_definitions
                )
                print(f"\n   {metric_name}: {score} (Expected: {case.get('expected_intent', 'unknown')})")
            elif metric_name == "ToolCallAccuracy":
                if "tool_calls" in case:
                    score = evaluator(
                        query=case["input"],
                        tool_calls=case["tool_calls"],
                        tool_definitions=flight_agent_tool_definitions
                    )
                else:
                    print(f"\n   {metric_name}: Skipped (missing tool_calls)")
                    continue
            elif metric_name == "TaskAdherence":
                score = evaluator(
                    query=case["input"],
                    response=case["output"],
                    tool_calls=case.get("tool_calls")
                )

            # Store and print the score
            case_results["metrics"][metric_name] = float(score)
            print(f"\n   {metric_name}: {score:.4f}")
            
        except Exception as e:
            print(f"\n   Error evaluating {metric_name}: {e}")
            case_results["metrics"][metric_name] = {"error": str(e)}
    
    results["test_cases"][case_id] = case_results

# Calculate aggregate metrics
aggregate_metrics = {}
for metric in metrics.keys():
    scores = [
        case_result["metrics"].get(metric) 
        for case_result in results["test_cases"].values()
        if isinstance(case_result["metrics"].get(metric), (int, float))
    ]
    if scores:
        aggregate_metrics[metric] = {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "count": len(scores)
        }

results["aggregate_metrics"] = aggregate_metrics

# Print overall results summary
print("\n=== Overall Evaluation Summary ===")
for metric, stats in aggregate_metrics.items():
    print(f"{metric}: Mean={stats['mean']:.4f}, Min={stats['min']:.4f}, Max={stats['max']:.4f}")

# Save results to file
results_dir = "evaluation_results"
os.makedirs(results_dir, exist_ok=True)
results_file = os.path.join(results_dir, f"flight_agent_eval_{run_id}.json")
with open(results_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nDetailed results saved to {results_file}")
```

**📝 What This Does:**
- Initializes evaluators for each metric
- Runs evaluations for each test case
- Collects and aggregates results
- Saves detailed results to a JSON file for future reference
- Calculates summary statistics for each metric

</details>

#### Step 4: Run Baseline Evaluation

Now that we've built our evaluation framework, let's establish a baseline with the current model.

**🎯 What This Step Accomplishes:**
- Measures current performance with the existing LLM
- Creates a reference point for comparison
- Identifies areas of strength and weakness

Execute the script to evaluate your flight agent:

```bash
cd voice_agent/app/backend
python -m tests.test_flight_agent_evaluation
```

The output will display scores for each evaluator across all test cases, along with aggregate metrics.

**📊 Sample Output:**
```
=== Flight Agent Evaluation Results (Model: gpt-4o-mini) ===

***** Test Case 1: I want to book a flight from New York to London on May 10th

   Groundedness: 0.8765

   Coherence: 0.9321

   Relevance: 0.9567

   IntentResolution: 0.9123 (Expected: flight booking)

   ToolCallAccuracy: 0.8876

   TaskAdherence: 0.9012

***** Test Case 2: What is the baggage allowance for economy class?
...

=== Overall Evaluation Summary ===
Groundedness: Mean=0.8843, Min=0.8234, Max=0.9321
Coherence: Mean=0.9176, Min=0.8765, Max=0.9567
Relevance: Mean=0.9432, Min=0.9012, Max=0.9876
IntentResolution: Mean=0.9021, Min=0.8543, Max=0.9456
ToolCallAccuracy: Mean=0.8832, Min=0.8234, Max=0.9321
TaskAdherence: Mean=0.9087, Min=0.8654, Max=0.9432

Detailed results saved to evaluation_results/flight_agent_eval_gpt-4o-mini-20250618-142536.json
```

#### Step 5: Analyze Baseline Results

After running the evaluation, it's time to interpret the results systematically.

**🎯 What This Step Accomplishes:**
- Identifies specific performance patterns
- Pinpoints areas for improvement
- Sets expectations for model upgrades

##### 📊 Interpreting Evaluation Metrics

| Metric | What Good Looks Like | What Bad Looks Like | How to Improve |
|--------|----------------------|--------------------|----------------|
| **Groundedness** | Facts match source context | Fabricated details | Better context handling in agent prompts |
| **Coherence** | Logical, well-structured responses | Confusing or contradictory answers | Enhance system prompts with structure guidance |
| **Relevance** | Direct answers to user queries | Off-topic or tangential responses | Improve intent detection and focus directives |
| **IntentResolution** | Correctly identifies user needs | Misunderstands user requests | Enhance intent categorization in prompts |
| **ToolCallAccuracy** | Correct tools with proper parameters | Wrong tools or invalid parameters | Better tool documentation in system prompts |
| **TaskAdherence** | Stays on task consistently | Gets distracted or veers off-topic | Add focus directives in system prompts |

##### Finding Patterns in Test Results

Look for patterns across your test cases:

1. **Are certain metrics consistently low?** This suggests a systematic issue.
2. **Do specific scenarios perform poorly?** This may indicate domain knowledge gaps.
3. **Are there outlier cases?** These may reveal edge case handling issues.
4. **How do complex vs. simple queries compare?** This shows scaling with complexity.

**📝 Document Your Findings:**
Create a baseline findings document that captures:
- Current performance levels across all metrics
- Specific areas of strength and weakness
- Hypotheses about what might improve with a model upgrade
- Priority areas for improvement

#### Step 6: Upgrade the LLM

Now it's time to evaluate an upgraded model to see if it addresses the issues identified in the baseline.

**🎯 What This Step Accomplishes:**
- Changes the deployed model to a newer or more capable version
- Prepares for comparative evaluation
- Implements best practices for model transitions

**Option A: Update Local Environment for Testing**

Edit the `.env` file in the backend directory to use a different model:

```
# Change this:
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini

# To this:
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
```

**Option B: Test Multiple Models in Script**

Alternatively, you can modify the evaluation script to test multiple models in a single run:

```python
# Add at the top of your script
models_to_test = ["gpt-4o-mini", "gpt-4o"]

# Then modify the evaluation loop to iterate through models
for model in models_to_test:
    model_config = {
        "azure_deployment": model,
        "azure_endpoint": endpoint,
        "api_key": api_key
    }
    # Run evaluation with this model...
```

**📋 Model Upgrade Best Practices:**
1. **Start with testing**, not production deployment
2. **Document the upgrade** process and expected outcomes
3. **Configure fallback mechanisms** in case of issues
4. **Monitor closely** after upgrading

#### Step 7: Run Comparative Evaluation

Run the evaluation with the new model to see the performance differences.

**🎯 What This Step Accomplishes:**
- Collects performance data on the upgraded model
- Enables direct comparison with baseline
- Provides evidence for upgrade decisions

Execute the script again with the new model:

```bash
cd voice_agent/app/backend
python -m tests.test_flight_agent_evaluation
```

The results will be saved to a new file with the new model name in the ID.

#### Step 8: Analyze Performance Improvements

Compare the results between models to quantify improvements and identify any new issues.

**🎯 What This Step Accomplishes:**
- Quantifies the benefits of the model upgrade
- Identifies any regressions or unexpected behavior
- Provides data for cost-benefit analysis

##### 📊 Creating a Comparative Analysis

Create a comparison between the models using the saved result files:

```python
# Sample comparison script (add to your evaluation script if desired)
import json
import os
import matplotlib.pyplot as plt

def compare_results(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        results1 = json.load(f1)
        results2 = json.load(f2)
    
    model1 = results1["model"]
    model2 = results2["model"]
    
    metrics = list(results1["aggregate_metrics"].keys())
    model1_scores = [results1["aggregate_metrics"][m]["mean"] for m in metrics]
    model2_scores = [results2["aggregate_metrics"][m]["mean"] for m in metrics]
    
    # Print comparison
    print(f"\n=== Model Comparison: {model1} vs {model2} ===")
    for i, metric in enumerate(metrics):
        diff = model2_scores[i] - model1_scores[i]
        print(f"{metric}: {model1}={model1_scores[i]:.4f}, {model2}={model2_scores[i]:.4f}, " +
              f"Difference: {diff:.4f} ({diff/model1_scores[i]*100:.2f}%)")
    
    # Optional: Create visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(metrics))
    width = 0.35
    ax.bar([i - width/2 for i in x], model1_scores, width, label=model1)
    ax.bar([i + width/2 for i in x], model2_scores, width, label=model2)
    ax.set_ylabel('Score')
    ax.set_title('Model Comparison by Metric')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    plt.savefig(f"evaluation_results/comparison_{model1}_vs_{model2}.png")
    
    return {
        "model1": model1,
        "model2": model2,
        "metrics": {
            m: {
                "model1_score": results1["aggregate_metrics"][m]["mean"],
                "model2_score": results2["aggregate_metrics"][m]["mean"],
                "difference": results2["aggregate_metrics"][m]["mean"] - results1["aggregate_metrics"][m]["mean"],
                "percent_change": (results2["aggregate_metrics"][m]["mean"] - results1["aggregate_metrics"][m]["mean"]) / 
                                results1["aggregate_metrics"][m]["mean"] * 100
            } for m in metrics
        }
    }

# Usage:
# comparison = compare_results("evaluation_results/flight_agent_eval_gpt-4o-mini-20250618-142536.json", 
#                           "evaluation_results/flight_agent_eval_gpt-4o-20250618-143045.json")
```

**📊 Key Metrics to Compare:**

1. **Overall metrics improvement**: How much better is the new model across all metrics?
2. **Performance on weak areas**: Did the new model address specific weaknesses?
3. **Consistency**: Is performance more consistent across different test cases?
4. **Error rates**: Are there fewer errors or failures?

**📈 Sample Comparison Output:**
```
=== Model Comparison: gpt-4o-mini vs gpt-4o ===
Groundedness: gpt-4o-mini=0.8843, gpt-4o=0.9321, Difference: 0.0478 (5.41%)
Coherence: gpt-4o-mini=0.9176, gpt-4o=0.9543, Difference: 0.0367 (4.00%)
Relevance: gpt-4o-mini=0.9432, gpt-4o=0.9654, Difference: 0.0222 (2.35%)
IntentResolution: gpt-4o-mini=0.9021, gpt-4o=0.9487, Difference: 0.0466 (5.17%)
ToolCallAccuracy: gpt-4o-mini=0.8832, gpt-4o=0.9376, Difference: 0.0544 (6.16%)
TaskAdherence: gpt-4o-mini=0.9087, gpt-4o=0.9432, Difference: 0.0345 (3.80%)
```

#### Step 9: Document Findings and Next Steps

Prepare a comprehensive analysis of your findings to guide the upgrade decision.

**🎯 What This Step Accomplishes:**
- Creates clear documentation of the evaluation process
- Provides evidence-based recommendations
- Establishes a framework for future evaluations

**📝 Recommended Documentation Structure:**

1. **Executive Summary**
   - Overall findings and recommendations
   - Key metrics improvements
   - Cost-benefit analysis

2. **Detailed Evaluation Results**
   - Comparison across all metrics
   - Test case analysis
   - Visualizations of improvements

3. **Implementation Recommendations**
   - Suggested deployment approach
   - Required system changes
   - Monitoring recommendations

4. **Next Steps**
   - Additional testing needed
   - System prompt adjustments
   - Future evaluation schedule

**⚙️ Best Practices for Production Upgrades**

1. **Implement gradual rollout**:
   - Start with a small percentage of traffic
   - Monitor closely for issues
   - Gradually increase traffic if performance is good

2. **Set up comprehensive monitoring**:
   - Track key metrics in real-time
   - Set alerts for performance degradation
   - Implement automated fallbacks if needed

3. **Maintain model versioning**:
   - Document all model changes
   - Keep previous model available as fallback
   - Track changes in performance over time

4. **Regular re-evaluation**:
   - Schedule periodic evaluations
   - Add new test cases as issues are discovered
   - Continuously improve evaluation framework

#### What You've Learned

By completing this exercise, you've gained valuable skills in:

- **Systematic LLM evaluation** using industry-standard metrics
- **Comparative analysis** of different AI models
- **Data-driven decision making** for AI system improvements
- **Best practices** for model upgrades in production environments
- **Performance monitoring** and tracking methodologies
- **Documentation** of AI system changes and improvements

These skills are essential for maintaining high-quality AI systems in production and making informed decisions about model upgrades and changes.

#### Further Resources

- [Azure AI Evaluation SDK Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/evaluation)
- [LLM Evaluation Best Practices](https://learn.microsoft.com/en-us/azure/machine-learning/concept-model-evaluation-llm)
- [Azure OpenAI Model Comparison Guide](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)

This approach provides quantitative metrics to measure the impact of upgrading your agent's LLM and helps ensure that changes maintain or improve the user experience.

## Security/Safety Persona

### Exercise 1: Adversarial Testing and Safety Evaluation

#### Learning Objectives
By completing this exercise, you will learn how to:
- Use Azure AI Evaluation SDK simulators to test system resilience
- Identify potential security vulnerabilities in AI agents
- Implement safety measures and content filtering
- Evaluate AI system behavior under adversarial conditions

#### Prerequisites
- Completed PM/Developer exercises
- Understanding of AI safety concepts
- Access to Azure AI Foundry evaluation tools

#### Estimated Time
90 minutes

#### Overview
Use Evaluation SDK simulators to attempt adversarial attacks on the system and identify areas where additional safety measures are needed.

**Reference:** [Azure AI Foundry Simulator Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data)

**✅ Success Criteria:** Identify vulnerabilities and implement appropriate safety measures.

### Exercise 2: Content Safety Filter Implementation

#### Learning Objectives
Test the car rental agent's safety compliance and implement content filtering where needed.

#### Estimated Time
60 minutes

#### Overview
When the car rental agent fails safety tests, implement appropriate filters and retest to ensure compliance.

**✅ Success Criteria:** Car rental agent passes all safety evaluations after filter implementation.

### Exercise 3: Identity-Based Access Control

#### Learning Objectives
By completing this exercise, you will learn how to:
- Implement user identity-based access control
- Demonstrate data scope limitations based on user identity
- Prevent unauthorized access to sensitive data

#### Estimated Time
60 minutes

#### Overview
Showcase that agents operate using logged-in user identity rather than service principals, ensuring proper data access control.

**✅ Success Criteria:** Demonstrate that datastore access is properly scoped to user identity.

### Exercise 4: Real-time Monitoring (Future Enhancement)

> **📝 Note:** This exercise will be available once real-time monitoring functionality is integrated into the AI Foundry Agent Service (planned post-Build 2025).

Real-time monitoring around generative quality and safety (Responsible AI) implementation.

---
#### Navigation: [Home](../../README.md) | [Previous Section](../03_observability/README.md)
