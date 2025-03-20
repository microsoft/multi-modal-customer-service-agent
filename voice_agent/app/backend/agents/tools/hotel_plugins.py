from typing import Annotated, Any  
from semantic_kernel.functions import kernel_function  
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from datetime import datetime  
import random  
import os  
import json  
from dotenv import load_dotenv  
from pathlib import Path  
from scipy import spatial  
from openai import AzureOpenAI  
  
# Load environment variables  
env_path = Path('../../../') / 'secrets.env'  
load_dotenv(dotenv_path=env_path)  
  
# Constants for Azure OpenAI  
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")  
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
AZURE_OPENAI_EMB_ENDPOINT = os.getenv("AZURE_OPENAI_EMB_ENDPOINT", AZURE_OPENAI_ENDPOINT)
AZURE_OPENAI_EMB_API_KEY = os.getenv("AZURE_OPENAI_EMB_API_KEY", AZURE_OPENAI_API_KEY)  
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
  
# SQLAlchemy setup  
Base = declarative_base()  
engine = create_engine('sqlite:///../../../data/hotel.db')  
Session = sessionmaker(bind=engine)  
session = Session()  
  
# Database models  
class Customer(Base):  
    __tablename__ = 'customers'  
    id = Column(String, primary_key=True)  
    name = Column(String)  
    reservations = relationship('Reservation', backref='customer')  
  
class Reservation(Base):  
    __tablename__ = 'reservations'  
    id = Column(Integer, primary_key=True, autoincrement=True)  
    customer_id = Column(String, ForeignKey('customers.id'))  
    hotel_id = Column(String)  
    room_type = Column(String)  
    check_in_date = Column(DateTime)  
    check_out_date = Column(DateTime)  
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
  
# Utility function for querying reservations  
def query_reservation_by_id(reservation_id: str):  
    return session.query(Reservation).filter_by(id=reservation_id, status="booked").first()  
  
# Kernel functions  
class Hotel_Tools:  
    """Class to hold hotel-related tools."""  
    agent_name = "hotel_agent"
  
    @kernel_function(  
        name="search_hotel_knowledgebase",  
        description="Search the hotel knowledge base to answer hotel policy questions."  
    )  
    async def search_hotel_knowledgebase(self, 
        search_query: Annotated[str, "The search query to use to search the knowledge base."]  
    ) -> str:  
        return SearchClient("../../../data/hotel_policy.json").find_article(search_query)  
    
    @kernel_function(  
        name="query_rooms",  
        description="Query the list of available rooms for a given hotel, check-in date, and check-out date."  
    )  
    async def query_rooms(self,  
        hotel_id: Annotated[str, "The hotel id."],  
        check_in_date: Annotated[str, "The check-in date."],  
        check_out_date: Annotated[str, "The check-out date."]  
    ) -> str:  
        room_types = ["Standard", "Deluxe", "Suite"]  
        return "\n".join(  
            f"Room type: {room_type}, Hotel ID: {hotel_id}, Check-in: {check_in_date}, Check-out: {check_out_date}, Status: Available"  
            for room_type in room_types  
        )  
    
    @kernel_function(  
        name="check_reservation_status",  
        description="Checks the reservation status for a booking."  
    )  
    async def check_reservation_status(self,  
        reservation_id: Annotated[str, "The reservation id."]  
    ) -> str:  
        reservation = query_reservation_by_id(reservation_id)  
        if reservation:  
            return json.dumps({  
                'reservation_id': reservation.id,  
                'customer_id': reservation.customer_id,  
                'room_type': reservation.room_type,  
                'hotel_id': reservation.hotel_id,  
                'check_in_date': reservation.check_in_date.strftime('%Y-%m-%d'),  
                'check_out_date': reservation.check_out_date.strftime('%Y-%m-%d'),  
                'status': reservation.status  
            })  
        return f"Cannot find status for the reservation with ID {reservation_id}"  
    
    @kernel_function(  
        name="confirm_reservation_change",  
        description="Execute the reservation change after confirming with the customer."  
    )  
    async def confirm_reservation_change(self,  
        current_reservation_id: Annotated[str, "The current reservation id."],  
        new_room_type: Annotated[str, "The new room type."],  
        new_check_in_date: Annotated[str, "The new check-in date."],  
        new_check_out_date: Annotated[str, "The new check-out date."]  
    ) -> str:  
        charge = 50  
        old_reservation = query_reservation_by_id(current_reservation_id)  
        if old_reservation:  
            old_reservation.status = "cancelled"  
            session.commit()  
    
            new_reservation_id = str(random.randint(100000, 999999))  
            new_reservation = Reservation(  
                id=new_reservation_id,  
                customer_id=old_reservation.customer_id,  
                hotel_id=old_reservation.hotel_id,  
                room_type=new_room_type,  
                check_in_date=datetime.strptime(new_check_in_date, '%Y-%m-%d'),  
                check_out_date=datetime.strptime(new_check_out_date, '%Y-%m-%d'),  
                status="booked"  
            )  
            session.add(new_reservation)  
            session.commit()  
    
            return (  
                f"Your new reservation for a {new_room_type} room is confirmed. "  
                f"Check-in date: {new_check_in_date}, Check-out date: {new_check_out_date}. "  
                f"New reservation ID: {new_reservation_id}. A charge of ${charge} has been applied."  
            )  
        return "Could not find the current reservation to change."  
    
    @kernel_function(  
        name="check_change_reservation",  
        description="Check the feasibility and outcome of a presumed reservation change."  
    )  
    async def check_change_reservation(self,  
        current_reservation_id: Annotated[str, "The current reservation id."],  
        new_check_in_date: Annotated[str, "The new check-in date."],  
        new_check_out_date: Annotated[str, "The new check-out date."],  
        new_room_type: Annotated[str, "The new room type."]  
    ) -> str:  
        return "Changing your reservation will cost an additional $50."  
    
    @kernel_function(  
        name="load_user_reservation_info",  
        description="Loads the hotel reservation for a user."  
    )  
    async def load_user_reservation_info(self,  
        user_id: Annotated[str, "The user id."]  
    ) -> str:  
        reservations = session.query(Reservation).filter_by(customer_id=user_id, status="booked").all()  
        if not reservations:  
            return "Sorry, we cannot find any reservation information for you."  
        return json.dumps([  
            {  
                'room_type': reservation.room_type,  
                'hotel_id': reservation.hotel_id,  
                'check_in_date': reservation.check_in_date.strftime('%Y-%m-%d'),  
                'check_out_date': reservation.check_out_date.strftime('%Y-%m-%d'),  
                'reservation_id': reservation.id,  
                'status': reservation.status  
            }  
            for reservation in reservations  
        ])   
