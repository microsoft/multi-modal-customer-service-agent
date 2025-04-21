import os  
import random  
from datetime import datetime, timedelta  
from typing import List, Dict, Union, Tuple
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from dateutil import parser  
from .tools import Tool  
import json
Base = declarative_base()  

loan_details = {}
jsonl_path = os.path.join(os.path.dirname(__file__), 'loan_consultantation.jsonl')
jsonl_path = '../data/loan_consultantation.jsonl'

if os.path.exists(jsonl_path):
    with open(jsonl_path, 'r', encoding='utf-8') as file:
        for line in file:
            data = json.loads(line.strip())
            loan_details[data["topic_name"]] = data["details"]

class LoanAgentTool(Tool):
    def __init__(self):
        super().__init__()

    def expand_for_detail(self, topic_name: str) -> str:
        return loan_details.get(topic_name, f"No details found for '{topic_name}'.")
