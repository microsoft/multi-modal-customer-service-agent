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
          
