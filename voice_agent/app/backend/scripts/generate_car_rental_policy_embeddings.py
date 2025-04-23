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