from typing import Annotated, Any  
from semantic_kernel.functions import kernel_function  
import os
from openai import AzureOpenAI
import json
from scipy import spatial

# Constants for Azure OpenAI  
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
AZURE_OPENAI_EMB_ENDPOINT = os.getenv("AZURE_OPENAI_EMB_ENDPOINT", AZURE_OPENAI_ENDPOINT)
AZURE_OPENAI_EMB_API_KEY = os.getenv("AZURE_OPENAI_EMB_API_KEY", AZURE_OPENAI_API_KEY)  
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  

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

# Kernel functions  
class Car_Rental_Tools:
    """Tools for car rental agent to perform various rental operations"""

    @kernel_function(
        description="Search for available rental cars",
        name="search_cars"
    )
    async def search_cars(self, location: str, pickup_date: str, return_date: str) -> str:
        # Mock implementation - replace with actual car rental API
        return f"Found available cars in {location} from {pickup_date} to {return_date}: \n" \
               "1. Economy - Toyota Corolla ($45/day)\n" \
               "2. SUV - Honda CR-V ($65/day)\n" \
               "3. Luxury - BMW 5 Series ($95/day)"

    @kernel_function(
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
    

    @kernel_function(
        name="search_rental_policies",
        description="Search car rental and insurance policies for relevant information."
    )
    async def search_rental_policies(self, 
        search_query: Annotated[str, "The search query about rental or insurance policies."]
    ) -> str:
        return search_client.find_article(search_query)