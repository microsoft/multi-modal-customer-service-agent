from typing import Any  
from rtmt import Tool, ToolResult, ToolResultDirection  
import os  
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from datetime import datetime  
import random  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from pathlib import Path  
import json  
from scipy import spatial  # for calculating vector similarities for search  
  
# Load environment variables  
env_path = Path('../../../') / 'secrets.env'  
load_dotenv(dotenv_path=env_path)  
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")  
  
# SQLAlchemy setup  
Base = declarative_base()  
engine = create_engine('sqlite:///../../../data/hotel.db')  
Session = sessionmaker(bind=engine)  
session = Session()  
  
# Define your database models  
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
  
# Define your functions  
emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version="2023-12-01-preview",  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  
  
def get_embedding(text, model=emb_engine):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
# Search Client class  
class Search_Client():  
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
  
# Define your functions  
def transfer_conversation(user_request):  
    print("transfer_conversation!", user_request)  
    return f"{user_request}"  
  
def search_hotel_knowledgebase(search_query):  
    print("search_hotel_knowledgebase")  
    faiss_search_client = Search_Client("../../../data/hotel_policy.json")  
    return faiss_search_client.find_article(search_query, topk=3)  
  
def query_rooms(hotel_id, check_in_date, check_out_date):  
    print("query_rooms")  
    room_types = ["Standard", "Deluxe", "Suite"]  
    rooms = ""  
    for room_type in room_types:  
        rooms += f"Room type: {room_type}, Hotel ID: {hotel_id}, Check-in: {check_in_date}, Check-out: {check_out_date}, Status: Available\n"  
    return rooms  
  
def check_reservation_status(reservation_id):  
    print("check_reservation_status")  
    result = session.query(Reservation).filter_by(id=reservation_id, status="booked").first()  
    if result is not None:  
        output = {  
            'reservation_id': result.id,  
            'customer_id': result.customer_id,  
            'room_type': result.room_type,  
            'hotel_id': result.hotel_id,  
            'check_in_date': result.check_in_date.strftime('%Y-%m-%d'),  
            'check_out_date': result.check_out_date.strftime('%Y-%m-%d'),  
            'status': result.status  
        }  
    else:  
        output = f"Cannot find status for the reservation with ID {reservation_id}"  
    return str(output)  
  
def confirm_reservation_change(current_reservation_id, new_room_type, new_check_in_date, new_check_out_date):  
    charge = 50  
    old_reservation = session.query(Reservation).filter_by(id=current_reservation_id, status="booked").first()  
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
        return f"Your new reservation for a {new_room_type} room is confirmed. Check-in date is {new_check_in_date} and check-out date is {new_check_out_date}. Your new reservation ID is {new_reservation_id}. A charge of ${charge} has been applied for the change."  
    else:  
        return "Could not find the current reservation to change."  
  
def check_change_reservation(current_reservation_id, new_check_in_date, new_check_out_date, new_room_type):  
    charge = 50  
    return f"Changing your reservation will cost an additional ${charge}."  
  
def load_user_reservation_info(user_id):  
    print("load_user_reservation_info")  
    matched_reservations = session.query(Reservation).filter_by(customer_id=user_id, status="booked").all()  
    reservations_info = []  
    for reservation in matched_reservations:  
        reservation_info = {  
            'room_type': reservation.room_type,  
            'hotel_id': reservation.hotel_id,  
            'check_in_date': reservation.check_in_date.strftime('%Y-%m-%d'),  
            'check_out_date': reservation.check_out_date.strftime('%Y-%m-%d'),  
            'reservation_id': reservation.id,  
            'status': reservation.status  
        }  
        reservations_info.append(reservation_info)  
    if not reservations_info:  
        return "Sorry, we cannot find any reservation information for you."  
    return str(reservations_info)  
  
# Define tool functions  
async def hotel_search_tool(args: Any) -> ToolResult:  
    search_query = args['search_query']  
    result = search_hotel_knowledgebase(search_query)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def query_rooms_tool(args: Any) -> ToolResult:  
    hotel_id = args['hotel_id']  
    check_in_date = args['check_in_date']  
    check_out_date = args['check_out_date']  
    result = query_rooms(hotel_id, check_in_date, check_out_date)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def check_reservation_status_tool(args: Any) -> ToolResult:  
    reservation_id = args['reservation_id']  
    result = check_reservation_status(reservation_id)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def confirm_reservation_change_tool(args: Any) -> ToolResult:  
    current_reservation_id = args['current_reservation_id']  
    new_room_type = args['new_room_type']  
    new_check_in_date = args['new_check_in_date']  
    new_check_out_date = args['new_check_out_date']  
    result = confirm_reservation_change(current_reservation_id, new_room_type, new_check_in_date, new_check_out_date)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def check_change_reservation_tool(args: Any) -> ToolResult:  
    current_reservation_id = args['current_reservation_id']  
    new_check_in_date = args['new_check_in_date']  
    new_check_out_date = args['new_check_out_date']  
    new_room_type = args['new_room_type']  
    result = check_change_reservation(current_reservation_id, new_check_in_date, new_check_out_date, new_room_type)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def load_user_reservation_info_tool(args: Any) -> ToolResult:  
    user_id = args['user_id']  
    result = load_user_reservation_info(user_id)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  
  
async def transfer_conversation_tool(args: Any) -> ToolResult:  
    user_request = args['user_request']  
    result = transfer_conversation(user_request)  
    return ToolResult(result, ToolResultDirection.TO_SERVER)  

hotel_tools = {
    "search_hotel_knowledgebase": hotel_search_tool,
    "query_rooms": query_rooms_tool,
    "check_reservation_status": check_reservation_status_tool,
    "confirm_reservation_change": confirm_reservation_change_tool,
    "check_change_reservation": check_change_reservation_tool,
    "load_user_reservation_info": load_user_reservation_info_tool,
    "transfer_conversation": transfer_conversation_tool
}
