import yaml  
from typing import Any  
import os  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from datetime import datetime  
import random  
from dotenv import load_dotenv  
from openai import AsyncAzureOpenAI  
from pathlib import Path  
import json  
from scipy import spatial  # for calculating vector similarities for search  
# Load YAML file  
import yaml
# Load YAML file  
import asyncio
import time
import aiohttp
import urllib.request  
import json  
import os  
import ssl  
import os
import redis
import pickle
import base64
from typing import Dict


def load_entity(file_path, entity_name):  
    with open(file_path, 'r') as file:  
        data = yaml.safe_load(file)  
    for entity in data['agents']:  
        if entity.get('name') == entity_name:  
            return entity  
    return None  
  
# Load environment variables  
load_dotenv()  
async_client = AsyncAzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),  
) 
INTENT_SHIFT_API_KEY = os.environ.get("INTENT_SHIFT_API_KEY")
INTENT_SHIFT_API_URL = os.environ.get("INTENT_SHIFT_API_URL") 
INTENT_SHIFT_API_DEPLOYMENT=os.environ.get("INTENT_SHIFT_API_DEPLOYMENT")
AZURE_OPENAI_4O_MINI_DEPLOYMENT=os.environ.get("AZURE_OPENAI_4O_MINI_DEPLOYMENT")
  
def allowSelfSignedHttps(allowed):  
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):  
        ssl._create_default_https_context = ssl._create_unverified_context  
  
allowSelfSignedHttps(True)  
  
async def detect_intent(conversation): 
    if INTENT_SHIFT_API_URL:
        start_time = time.time() 
        # Prepare the request data  
        # Format the data according to the ServiceInput schema  
        value = f"{conversation}"  
        data = {  
            "input_data": {  
                "columns": ["input_string"],  
                "index": [0],  
                "data": [[value]]  # Wrap value in a list to match the expected structure  
            },  
            "params": {}  
        }  
        
        # Encode the data as JSON  
        body = json.dumps(data).encode('utf-8')  
        
        # Check if the API key is provided  
        if not INTENT_SHIFT_API_KEY:  
            raise Exception("A key should be provided to invoke the endpoint")  
        
        # Set the headers  
        headers = {  
            'Content-Type': 'application/json',  
            'Authorization': f'Bearer {INTENT_SHIFT_API_KEY}',  
            'azureml-model-deployment': INTENT_SHIFT_API_DEPLOYMENT  
        }  
        
        # Make the request  
        req = urllib.request.Request(INTENT_SHIFT_API_URL, body, headers=headers)  
    
        
        try:  
            response = urllib.request.urlopen(req)  
            result = response.read()
            result = json.loads(result)[0]['0'].strip()
            end_time = time.time()
            print(f"Job succeeded in {end_time - start_time:.2f} seconds.")
            return result
            
        except urllib.error.HTTPError as error:  
            print("The request failed with status code: " + str(error.code))  
            print(error.info())  
            print(error.read().decode("utf8", 'ignore'))  
            return None 
    else:
        # fallback to gpt-4o-mini
        messages = [
            {"role": "system", "content": "You are a classifier model whose job is to classify the intent of the most recent user question into one of the following domains:\n\n- **hotel_agent**: Deal with hotel reservations, confirmations, changes, and general hotel policy questions.\n- **flight_agent**: Deal with flight reservations, confirmations, changes, and general airline policy questions.\n\nYou must only respond with the name of the predicted agent."},
            {"role": "user", "content": conversation}
        ]
        response = await async_client.chat.completions.create(
            model=AZURE_OPENAI_4O_MINI_DEPLOYMENT,
            messages=messages,
            max_tokens=20
        )
        intent = response.choices[0].message.content.strip()
        return intent

class SessionState:  
    def __init__(self): 
        # Redis configuration 
        self.redis_client = None 
        AZURE_REDIS_ENDPOINT = os.getenv("AZURE_REDIS_ENDPOINT")  
        AZURE_REDIS_KEY = os.getenv("AZURE_REDIS_KEY")  
        if AZURE_REDIS_KEY: #use redis
            self.redis_client = redis.StrictRedis(host=AZURE_REDIS_ENDPOINT, port=6380, password=AZURE_REDIS_KEY, ssl=True)  
        else: #use in-memory
            self.session_store: Dict[str, Dict] = {}  

                
    def get(self, key):  
        if self.redis_client:
            self.data = self.redis_client.get(key)  
            return pickle.loads(base64.b64decode(self.data)) if self.data else None  
        else:
            return self.session_store.get(key)

          
    def set(self, key, value):  
        if self.redis_client:
            self.redis_client.set(key, base64.b64encode(pickle.dumps(value)))  
        else:
            self.session_store[key]=value
          
