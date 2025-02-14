import os  
import aiohttp  
import asyncio  
import json  
import yaml  
import logging  
from enum import Enum  
from typing import Any, Callable, Optional  
from aiohttp import web  
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  
from azure.core.credentials import AzureKeyCredential  
from utility import detect_intent, SessionState  
  
# Configure logging  
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")  
logger = logging.getLogger(__name__)  
  
class ToolResultDirection(Enum):  
    TO_SERVER = 1  
    TO_CLIENT = 2  
  
class ToolResult:  
    text: str  
    destination: ToolResultDirection  
  
    def __init__(self, text: str, destination: ToolResultDirection):  
        self.text = text  
        self.destination = destination  
  
    def to_text(self) -> str:  
        if self.text is None:  
            return ""  
        return self.text if type(self.text) == str else json.dumps(self.text)  
  
class Tool:  
    target: Callable[..., ToolResult]  
    schema: Any  
  
    def __init__(self, target: Any, schema: Any):  
        self.target = target  
        self.schema = schema  
  
class RTMiddleTier:  
    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):  
        self.sessions = {}  # Track sessions  
        self.endpoint = endpoint  
        self.deployment = deployment  
        self.key = credentials.key if isinstance(credentials, AzureKeyCredential) else None  
        self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default") if not self.key else None  
  
    async def _connect_to_openai(self, session_key: str):  
        session = self.sessions[session_key]  
        langs = list(session["languages"].values())  
        system_prompt = f"Translate between {langs[0]} and {langs[1]}. Maintain context."  
  
        params = {"api-version": "2024-10-01-preview", "deployment": self.deployment}  
        if self._token_provider:  
            headers = {"Authorization": f"Bearer {self._token_provider()}"}  
        else:  
            headers = {"api-key": self.key}    
        async with aiohttp.ClientSession() as session:  
            target_ws = await session.ws_connect(  
                f"{self.endpoint}/openai/realtime",  
                headers=headers,  
                params=params  
            )  
            await target_ws.send_json({  
                "type": "session.update",  
                "session": {"instructions": system_prompt}  
            })  
            return target_ws  
  
    async def _forward_messages(self, client_ws: web.WebSocketResponse, session_key: str):  
        session = self.sessions[session_key]  
  
        if not session["target_ws"]:  
            session["target_ws"] = await self._connect_to_openai(session_key)  
  
        async def from_client_to_server():  
            async for msg in client_ws:  
                if msg.type == aiohttp.WSMsgType.TEXT:  
                    await self._process_client_message(msg, client_ws, session)  
  
        async def from_server_to_client():  
            async for msg in session["target_ws"]:  
                if msg.type == aiohttp.WSMsgType.TEXT:  
                    await self._broadcast_to_clients(msg, client_ws, session)  
  
        await asyncio.gather(from_client_to_server(), from_server_to_client())  
  
    async def _process_client_message(self, msg, client_ws, session):  
        message = json.loads(msg.data)  
        if message["type"] == "conversation.item.input_audio_transcription.completed":  
            source_lang = session["languages"][id(client_ws)]  
            target_lang = next((lang for cid, lang in session["languages"].items() if cid != id(client_ws)), None)  
  
            message["transcript"] = f"Translate from {source_lang} to {target_lang}: {message['transcript']}"  
            await session["target_ws"].send_json(message)  
  
    async def _broadcast_to_clients(self, msg, sender_ws, session):  
        translated_message = json.loads(msg.data)  
        for client in session["clients"]:  
            if client != sender_ws:  
                await client.send_json(translated_message)  
  
    async def _handler_with_session_key(self, request: web.Request):  
        session_key = request.query.get("session_state_key", "default")  
        lang = request.query.get("lang", "en")  
  
        if session_key not in self.sessions:  
            self.sessions[session_key] = {  
                "clients": [],  
                "target_ws": None,  
                "languages": {}  
            }  
        session = self.sessions[session_key]  
  
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
        session["clients"].append(ws)  
        session["languages"][id(ws)] = lang  
  
        try:  
            await self._forward_messages(ws, session_key)  
        finally:  
            session["clients"].remove(ws)  
            if not session["clients"]:  
                del self.sessions[session_key]  
  
    def attach_to_app(self, app, path):  
        app.router.add_get(path, self._handler_with_session_key)  