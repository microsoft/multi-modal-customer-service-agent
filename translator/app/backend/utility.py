import os  
from datetime import datetime  
import random  
from dotenv import load_dotenv  
from openai import AsyncAzureOpenAI  
from pathlib import Path  
from aiohttp import web  
import numpy as np
import json  
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
from typing import Any, Callable, Optional, Dict, List  
from enum import Enum  
import struct  
from typing import List  

class ToolResultDirection(Enum):  
    TO_SERVER = 1  
    TO_CLIENT = 2  
  
class ToolResult:  
    def __init__(self, text: str, destination: ToolResultDirection):  
        self.text = text  
        self.destination = destination  
  
    def to_text(self) -> str:  
        if self.text is None:  
            return ""  
        return self.text if isinstance(self.text, str) else json.dumps(self.text)  
  
class Tool:  
    def __init__(self, target: Any, schema: Any):  
        self.target = target  
        self.schema = schema  
  
class Session:  
    def __init__(self):  
        self.client_language_mapping: Dict[str, str] = {}
        self.lock = asyncio.Lock()  
        self.user_languages: List[str] = []   
        self.system_prompt: Optional[str] = None  
        self.ready = False  
        # Per client queues for sending and receiving data to/from OpenAI.  
        self.client_output_queues: Dict[web.WebSocketResponse, asyncio.Queue] = {}
        self.client_to_realtime_queues: Dict[web.WebSocketResponse, asyncio.Queue] = {}
        self.azure_workers: Dict[web.WebSocketResponse, asyncio.Task] = {}
        self.client_language_mapping: Dict[str, str] = {}
        self.client_id_mapping: Dict[web.WebSocketResponse, str] = {}
        # To record the partner for each client
        self.partner_mapping: Dict[web.WebSocketResponse, web.WebSocketResponse] = {}
        
       
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
          

  
def mix_audio_buffers(buffers: List[bytes]) -> bytes:  
    """Mixes a list of raw PCM 16-bit single-channel byte sequences by summing them sample-by-sample,  
    clipping the results to the 16-bit signed integer range, and returning the resulting 16-bit PCM bytes."""  
      
    if not buffers:  
        return b""  
      
    # Convert each buffer into a NumPy array of signed 16-bit integers.  
    np_buffers = [np.frombuffer(b, dtype=np.int16) for b in buffers]  
      
    # Find the length of the shortest buffer and truncate others to this length.  
    min_len = min(len(b) for b in np_buffers)  
    np_buffers = [b[:min_len] for b in np_buffers]  
      
    # Stack arrays vertically and sum along the first axis (sample-by-sample sum).  
    sum_array = np.sum(np.vstack(np_buffers), axis=0)  
      
    # Clip the results to the 16-bit signed integer range.  
    clipped_array = np.clip(sum_array, -32768, 32767).astype(np.int16)  
      
    # Convert the clipped array back to bytes.  
    return clipped_array.tobytes()  
  
