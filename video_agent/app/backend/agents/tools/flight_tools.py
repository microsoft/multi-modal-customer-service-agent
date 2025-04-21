import os  
import json  
import random  
import uuid  
from datetime import datetime, timedelta  
from typing import Any  
from pathlib import Path  

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from scipy import spatial  # for calculating vector similarities for search  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from dateutil import parser  
  
from rtmt import Tool, ToolResult, ToolResultDirection  
  
# Load environment variables  
env_path = Path('.') / 'secrets.env'  
load_dotenv(dotenv_path=env_path)  
  
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version="2023-12-01-preview",  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  
  
# SQLAlchemy setup  
sqllite_db_path = os.environ.get("SQLITE_DB_PATH", "../../../data/flight_db.db")  
engine = create_engine(f'sqlite:///{sqllite_db_path}')  
Base = declarative_base()  
Session = sessionmaker(bind=engine)  
session = Session()  
  
# Define your database models  
class Customer(Base):  
    __tablename__ = 'customers'  
    id = Column(String, primary_key=True)  
    name = Column(String)  
    flights = relationship('Flight', backref='customer')  
  
class Flight(Base):  
    __tablename__ = 'flights'  
    id = Column(Integer, primary_key=True, autoincrement=True)  
    customer_id = Column(String, ForeignKey('customers.id'))  
    ticket_num = Column(String)  
    flight_num = Column(String)  
    airline = Column(String)  
    seat_num = Column(String)  
    departure_airport = Column(String)  
    arrival_airport = Column(String)  
    departure_time = Column(DateTime)  
    arrival_time = Column(DateTime)  
    ticket_class = Column(String)  
    gate = Column(String)  
    status = Column(String)  
  
Base.metadata.create_all(engine)  
  
# Define your functions  
def transfer_conversation(user_request):  
    print("transfer_conversation!", user_request)  
    return f"{user_request}"  
def get_embedding(text, model=emb_engine):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
# Search Client class  
class Search_Client:  
    def __init__(self, emb_map_file_path):  
        with open(emb_map_file_path) as file:  
            self.chunks_emb = json.load(file)  
  
    def find_article(self, question, topk=3):  
        """Given an input vector and a dictionary of label vectors,  
        returns the label with the highest cosine similarity to the input vector."""  
        print("question ", question)  
        input_vector = get_embedding(question, model=emb_engine)  
        # Compute cosine similarity between input vector and each label vector  
        cosine_list = []  
        for item in self.chunks_emb:  
            cosine_sim = 1 - spatial.distance.cosine(input_vector, item['policy_text_embedding'])  
            cosine_list.append((item['id'], item['policy_text'], cosine_sim))  
        cosine_list.sort(key=lambda x: x[2], reverse=True)  
        cosine_list = cosine_list[:topk]  
        best_chunks = [chunk[0] for chunk in cosine_list]  
        contents = [chunk[1] for chunk in cosine_list]  
        text_content = ""  
        for chunk_id, content in zip(best_chunks, contents):  
            text_content += f"{chunk_id}\n{content}\n"  
        return text_content  
  
def search_airline_knowledgebase(search_query):  
    print("search_airline_knowledgebase")  
    faiss_search_client = Search_Client("../../../data/flight_policy.json")  
    return faiss_search_client.find_article(search_query, topk=3)  
  
def query_flights(from_, to, departure_time):  
    print("query_flights")  
    def get_new_times(departure_time, delta):  
        dp_dt = parser.parse(departure_time)  
        new_dp_dt = dp_dt + timedelta(hours=delta)  
        new_ar_dt = new_dp_dt + timedelta(hours=2)  
        new_departure_time = new_dp_dt.strftime("%Y-%m-%dT%H:%M:%S")  
        new_arrival_time = new_ar_dt.strftime("%Y-%m-%dT%H:%M:%S")  
        return new_departure_time, new_arrival_time  
    flights = ""  
    for flight_num, delta in [("AA479", -1), ("AA490", -2), ("AA423", -3)]:  
        new_departure_time, new_arrival_time = get_new_times(departure_time, delta)  
        flights += f"flight number {flight_num}, from: {from_}, to: {to}, departure_time: {new_departure_time}, arrival_time: {new_arrival_time}, flight_status: on time \n"  
    return flights  
  
def check_flight_status(flight_num, from_):  
    print("check_flight_status")  
    result = session.query(Flight).filter_by(flight_num=flight_num, departure_airport=from_, status="open").first()  
    if result is not None:  
        output = {  
            'flight_num': result.flight_num,  
            'departure_airport': result.departure_airport,  
            'arrival_airport': result.arrival_airport,  
            'departure_time': result.departure_time.strftime('%Y-%m-%d %H:%M'),  
            'arrival_time': result.arrival_time.strftime('%Y-%m-%d %H:%M'),  
            'status': result.status  
        }  
    else:  
        output = f"Cannot find status for the flight {flight_num} from {from_}"  
    return str(output)  
  
def confirm_flight_change(current_ticket_number, new_flight_number, new_departure_time, new_arrival_time):  
    charge = 80  
    old_flight = session.query(Flight).filter_by(ticket_num=current_ticket_number, status="open").first()  
    if old_flight:  
        old_flight.status = "cancelled"  
        session.commit()  
        new_ticket_num = str(random.randint(1000000000, 9999999999))  
        new_flight = Flight(  
            id=new_ticket_num,  
            ticket_num=new_ticket_num,  
            customer_id=old_flight.customer_id,  
            flight_num=new_flight_number,  
            seat_num=old_flight.seat_num,  
            airline=old_flight.airline,  
            departure_airport=old_flight.departure_airport,  
            arrival_airport=old_flight.arrival_airport,  
            departure_time=datetime.strptime(new_departure_time, '%Y-%m-%d %H:%M'),  
            arrival_time=datetime.strptime(new_arrival_time, '%Y-%m-%d %H:%M'),  
            ticket_class=old_flight.ticket_class,  
            gate=old_flight.gate,  
            status="open"  
        )  
        session.add(new_flight)  
        session.commit()  
        return f"Your new flight now is {new_flight_number} departing from {new_flight.departure_airport} to {new_flight.arrival_airport}. Your new departure time is {new_departure_time} and arrival time is {new_arrival_time}. Your new ticket number is {new_ticket_num}. Your credit card has been charged with an amount of ${charge} dollars for fare difference."  
    else:  
        return "Could not find the current ticket to change."  
  
def check_change_booking(current_ticket_number, current_flight_number, new_flight_number, from_):  
    charge = 80  
    return f"Changing your ticket from {current_flight_number} to new flight {new_flight_number} departing from {from_} would cost {charge} dollars."  
  
def load_user_flight_info(user_id):  
    print("load_user_flight_info")  
    matched_flights = session.query(Flight).filter_by(customer_id=user_id, status="open").all()  
    flights_info = []  
    for flight in matched_flights:  
        flight_info = {  
            'airline': flight.airline,  
            'flight_num': flight.flight_num,  
            'seat_num': flight.seat_num,  
            'departure_airport': flight.departure_airport,  
            'arrival_airport': flight.arrival_airport,  
            'departure_time': flight.departure_time.strftime('%Y-%m-%d %H:%M'),  
            'arrival_time': flight.arrival_time.strftime('%Y-%m-%d %H:%M'),  
            'ticket_class': flight.ticket_class,  
            'ticket_num': flight.ticket_num,  
            'gate': flight.gate,  
            'status': flight.status  
        }  
        flights_info.append(flight_info)  
    if not flights_info:  
        return "Sorry, we cannot find any flight information for you."  
    return str(flights_info)  
  
# Define tool functions  
async def search_airline_knowledgebase_tool(args: Any) -> ToolResult:  
    search_query = args['search_query']  
    result = search_airline_knowledgebase(search_query)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def query_flights_tool(args: Any) -> ToolResult:  
    from_ = args['from_']  
    to = args['to']  
    departure_time = args['departure_time']  
    result = query_flights(from_, to, departure_time)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def check_flight_status_tool(args: Any) -> ToolResult:  
    flight_num = args['flight_num']  
    from_ = args['from_']  
    result = check_flight_status(flight_num, from_)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def confirm_flight_change_tool(args: Any) -> ToolResult:  
    current_ticket_number = args['current_ticket_number']  
    new_flight_number = args['new_flight_number']  
    new_departure_time = args['new_departure_time']  
    new_arrival_time = args['new_arrival_time']  
    result = confirm_flight_change(current_ticket_number, new_flight_number, new_departure_time, new_arrival_time)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def check_change_booking_tool(args: Any) -> ToolResult: 
    print(" args ", args)
 
    current_ticket_number = args['current_ticket_number']  
    current_flight_number = args['current_flight_number']  
    new_flight_number = args['new_flight_number']  
    from_ = args['from_']  
    result = check_change_booking(current_ticket_number, current_flight_number, new_flight_number, from_)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def load_user_flight_info_tool(args: Any) -> ToolResult:  
    user_id = args['user_id']  
    result = load_user_flight_info(user_id)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
async def transfer_conversation_tool(args: Any) -> ToolResult:  
    user_request = args['user_request']  
    result = transfer_conversation(user_request)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  

flight_tools = {
    'search_airline_knowledgebase': search_airline_knowledgebase_tool,
    'query_flights': query_flights_tool,
    'check_flight_status': check_flight_status_tool,
    'confirm_flight_change': confirm_flight_change_tool,
    'check_change_booking': check_change_booking_tool,
    'load_user_flight_info': load_user_flight_info_tool,
    'transfer_conversation': transfer_conversation_tool
}
