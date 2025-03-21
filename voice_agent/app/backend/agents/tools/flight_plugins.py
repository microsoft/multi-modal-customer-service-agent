from typing import Annotated, Any  
from semantic_kernel.functions import kernel_function  
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship 
from sqlalchemy.exc import SQLAlchemyError 
from datetime import datetime, timedelta  
from dateutil import parser  
import random  
import os  
import json  
from dotenv import load_dotenv  
from pathlib import Path  
from scipy import spatial  
from openai import AzureOpenAI  
  
  
# Constants for Azure OpenAI  
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
AZURE_OPENAI_EMB_ENDPOINT = os.getenv("AZURE_OPENAI_EMB_ENDPOINT", AZURE_OPENAI_ENDPOINT)
AZURE_OPENAI_EMB_API_KEY = os.getenv("AZURE_OPENAI_EMB_API_KEY", AZURE_OPENAI_API_KEY)
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
  
# SQLAlchemy setup  
Base = declarative_base()  
sqllite_db_path = os.environ.get("SQLITE_DB_PATH", "../data/flight_db.db")  
engine = create_engine(f'sqlite:///{sqllite_db_path}')  
Session = sessionmaker(bind=engine)  
session = Session()  
  
# Database models  
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
search_client = SearchClient("../data/flight_policy.json")
def query_flight_by_ticket(ticket_num: str):  
    return session.query(Flight).filter_by(ticket_num=ticket_num, status="open").first()  
  
# Kernel functions  
class Flight_Tools:  
    """Class to hold flight-related tools."""  
    agent_name = "flight_agent"
  
    @kernel_function(  
        name="search_airline_knowledgebase",  
        description="Search the airline knowledge base to answer airline policy questions."  
    )  
    async def search_airline_knowledgebase(self,  
        search_query: Annotated[str, "The search query to use to search the knowledge base."]  
    ) -> str:  
        return search_client.find_article(search_query)  
  
    @kernel_function(  
        name="query_flights",  
        description="Query the list of available flights for a given departure airport code, arrival airport code and departure time."  
    )  
    async def query_flights(self,  
        from_: Annotated[str, "The departure airport code."],  
        to: Annotated[str, "The arrival airport code."],  
        departure_time: Annotated[str, "The departure time."]  
    ) -> str:  
        def get_new_times(departure_time, delta):  
            dp_dt = parser.parse(departure_time)  
            new_dp_dt = dp_dt + timedelta(hours=delta)  
            new_ar_dt = new_dp_dt + timedelta(hours=2)  
            return new_dp_dt.strftime("%Y-%m-%dT%H:%M:%S"), new_ar_dt.strftime("%Y-%m-%dT%H:%M:%S")  
  
        flights = ""  
        for flight_num, delta in [("AA479", -1), ("AA490", -2), ("AA423", -3)]:  
            new_departure_time, new_arrival_time = get_new_times(departure_time, delta)  
            flights += f"Flight number: {flight_num}, From: {from_}, To: {to}, Departure: {new_departure_time}, Arrival: {new_arrival_time}, Status: On time.\n"  
        return flights  
  
    @kernel_function(  
        name="check_flight_status",  
        description="Checks the flight status for a flight."  
    )  
    async def check_flight_status(self,  
        flight_num: Annotated[str, "The flight number."],  
        from_: Annotated[str, "The departure airport code."]  
    ) -> str:  
        flight = session.query(Flight).filter_by(flight_num=flight_num, departure_airport=from_, status="open").first()  
        if flight:  
            return json.dumps({  
                'flight_num': flight.flight_num,  
                'departure_airport': flight.departure_airport,  
                'arrival_airport': flight.arrival_airport,  
                'departure_time': flight.departure_time.strftime('%Y-%m-%d %H:%M'),  
                'arrival_time': flight.arrival_time.strftime('%Y-%m-%d %H:%M'),  
                'status': flight.status  
            })  
        return f"Cannot find status for the flight {flight_num} from {from_}."  
  
    @kernel_function(  
        name="confirm_flight_change",  
        description="Execute the flight change after confirming with the customer."  
    )  
    async def confirm_flight_change(self,  
        current_ticket_number: Annotated[str, "The current ticket number."],  
        new_flight_number: Annotated[str, "The new flight number."],  
        new_departure_time: Annotated[str, "The new departure time."],  
        new_arrival_time: Annotated[str, "The new arrival time."]  
    ) -> str:  
        charge = 80  
        old_flight = query_flight_by_ticket(current_ticket_number)  
        if old_flight:  
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
            try:
                with session.begin():
                    session.add(new_flight)
                    old_flight.status = "cancelled"
                    session.commit()

                return (f"Your new flight is {new_flight_number}, departing from {new_flight.departure_airport} to {new_flight.arrival_airport} "
                        f"on {new_departure_time}, arriving at {new_arrival_time}. Your new ticket number is {new_ticket_num}. "
                        f"Your credit card has been charged ${charge}.")
            except SQLAlchemyError as e:
                session.rollback()
                return f"Failed to change the flight due to an error: {str(e)}"  
 
        return "Could not find the current ticket to change."  
  
    @kernel_function(  
        name="check_change_booking",  
        description="Check the feasibility and outcome of a presumed flight change."  
    )  
    async def check_change_booking(self,  
        current_ticket_number: Annotated[str, "The current ticket number."],  
        current_flight_number: Annotated[str, "The current flight number."],  
        new_flight_number: Annotated[str, "The new flight number."],  
        from_: Annotated[str, "The departure airport code."]  
    ) -> str:  
        charge = 80  
        return f"Changing your ticket from {current_flight_number} to {new_flight_number}, departing from {from_}, would cost ${charge}."  
  
    @kernel_function(  
        name="load_user_flight_info",  
        description="Loads the flight information for a user."  
    )  
    async def load_user_flight_info(self,  
        user_id: Annotated[str, "The user id."]  
    ) -> str:  
        flights = session.query(Flight).filter_by(customer_id=user_id, status="open").all()  
        if not flights:  
            return "Sorry, we cannot find any flight information for you."  
        return json.dumps([  
            {  
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
            for flight in flights  
        ])  
