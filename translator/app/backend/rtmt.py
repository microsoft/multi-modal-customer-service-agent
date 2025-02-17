from __future__ import annotations
  
import os  
import aiohttp  
import asyncio  
import json  
import logging  
from enum import Enum  
from typing import Any, Callable, Optional, Dict, List  
from aiohttp import web  
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  
from azure.core.credentials import AzureKeyCredential  
  
# Configure logging  
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")  
logger = logging.getLogger(__name__)  
  
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
        self.clients: List[str] = []  
        self.openai_ws: Optional[aiohttp.ClientWebSocketResponse] = None  
        self.lock = asyncio.Lock()  
        self.user_languages: List[str] = []   
        self.translation_pairs: Dict[web.WebSocketResponse, str] = {}  
        self.system_prompt: Optional[str] = None  
        self.ready = False  
        self.handler_active = False  
  
class RTMiddleTier:  
    temperature: Optional[float] = None  
    max_tokens: Optional[int] = None  
    disable_audio: Optional[bool] = None  
  
    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):  
        self.session_lock = asyncio.Lock()  
        self.sessions: Dict[str, Session] = {}  
        self.endpoint = endpoint  
        self.deployment = deployment  

        self.key = credentials.key if isinstance(credentials, AzureKeyCredential) else None  
        self._token_provider = (  
            get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")  
            if not self.key  
            else None  
        )  
  
    async def handshake_handler(self, request: web.Request) -> web.Response:  
        action = request.query.get("action")  
        user_lang = request.query.get("user_lang")  
        is_ready = True
        if action == "create":  
            import uuid  
            session_key = str(uuid.uuid4())[:8]  
            async with self.session_lock:  
                if session_key not in self.sessions:  
                    session = Session()  
                    session.user_languages.append(user_lang) 

                    self.sessions[session_key] = session 

                else:  
                    return web.json_response({"status": "error", "error": "UUID collision"}, status=500)  

            return web.json_response({"status": "ok", "session_key": session_key, "ready": False, "partner_lang": None})  
  
        elif action == "join":  
            session_key = request.query.get("session_key")  
            if not session_key or not user_lang:  
                return web.json_response({"status": "error", "error": "Missing parameters"}, status=400)  
            async with self.session_lock:  
                if session_key not in self.sessions:  
                    return web.json_response({"status": "error", "error": "Invalid session_key"}, status=404)  
                session = self.sessions[session_key]  
                session.user_languages.append(user_lang)  
                partner_lang = [lang for lang in session.user_languages if  lang != user_lang][0] if len(session.user_languages) > 1 else None 
                session.system_prompt = f"""You are an AI translator to help translate conversations between two people speaking {partner_lang} and {user_lang}. When a person speaks {partner_lang}, you translate to {user_lang}, and when a person speaks {user_lang}, then translate to {partner_lang}."""
                logger.info("joining, my lang: %s, partner_lang: %s", user_lang, partner_lang)

                return web.json_response({"status": "ok", "session_key": session_key, "ready": True, "partner_lang": partner_lang})  
  
        elif action == "status":  
            session_key = request.query.get("session_key")  
            if not session_key:  
                return web.json_response({"status": "error", "error": "Missing session_key"}, status=400)  
            async with self.session_lock:  
                if session_key not in self.sessions:  
                    return web.json_response({"status": "error", "error": "Invalid session_key"}, status=404)  
                session = self.sessions[session_key]  
                partner_lang = [lang for lang in session.user_languages if  lang != user_lang][0] if len(session.user_languages) > 1 else None 
                if partner_lang is None:
                    is_ready = False
                    status = "ok"
                else:
                    is_ready = True
                    status = "ok"
                logger.info("status polling, my lang: %s, partner_lang: %s", user_lang, partner_lang)

                return web.json_response({"status": status, "session_key": session_key, "ready": is_ready, "partner_lang": partner_lang})  
  
        else:  
            return web.json_response({"status": "error", "error": "Invalid action"}, status=400)  
  
  
    async def _process_message_to_client(self, msg: str) -> Optional[dict]:  
        message = json.loads(msg.data)  
        updated_message = msg.data 
        logger.info("message type sent back: %s", message['type']) 
        if message is not None:  
            if "delta" not in message:  
                if message["type"] == "error":  
                    logger.error(message)  
            match message["type"]:  
                case "session.created":  
                    logger.info("session created")  
                    session = message["session"]  
                    session["instructions"] = ""  
                    session["tools"] = []  
                    session["tool_choice"] = "none"  
                    session["max_response_output_tokens"] = None  
                    updated_message = json.dumps(message)  
        return updated_message  
  
    async def _process_message_to_server(self, msg: dict, system_prompt: str) -> Optional[dict]: 
        # logger.info("system_prompt: \n %s", system_prompt) 

        message = json.loads(msg.data)  
        logger.info("message type sent to server: \n %s", message["type"]) 
        updated_message = msg.data  
        if message is not None:  
            match message["type"]:  
                case "session.update":  
                    session = message["session"]  
                    session["instructions"] = system_prompt  
                    if self.temperature is not None:  
                        session["temperature"] = self.temperature  
                    if self.max_tokens is not None:  
                        session["max_response_output_tokens"] = self.max_tokens  
                    if self.disable_audio is not None:  
                        session["disable_audio"] = self.disable_audio  
                    updated_message = json.dumps(message)  
        return updated_message  

  
    async def _handler_with_session_key(self, request: web.Request):  
        session_key = request.query.get("session_key")  
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
        async with self.session_lock:  
            if session_key not in self.sessions:  
                # return ws  
                session = Session()  
                session.system_prompt = f"""You are an AI translator to help translate conversations between two people speaking English and Vietnamese. When a person speaks Vienamese, you translate to English, and when a person speaks English, then translate to Vietnamese. Just translate what is said"""
                self.sessions[session_key] = session 

            session = self.sessions[session_key]  
        async with session.lock:  
            if len(session.clients) >= 2:  
                session.ready = True  
        # logger.info("system_prompt: \n %s", session.system_prompt)
        await self._forward_messages(session_key, ws)
        return ws  
    async def _forward_messages(self, session_key: str, ws: web.WebSocketResponse):  
        logger.info("session_key: %s", session_key)
        session = self.sessions[session_key]  
        target_ws = None
        system_prompt = session.system_prompt
        async with aiohttp.ClientSession(base_url=self.endpoint) as session:  
            params = {"api-version": "2024-10-01-preview", "deployment": self.deployment}  
            headers = {}  
            if "x-ms-client-request-id" in ws.headers:  
                headers["x-ms-client-request-id"] = ws.headers["x-ms-client-request-id"]  
            if self.key is not None:  
                headers = {"api-key": self.key}  
            else:  
                headers = {"Authorization": f"Bearer {self._token_provider()}"}  
  
            async with session.ws_connect("/openai/realtime", headers=headers, params=params) as target_ws:  
    
                async def from_client_to_server():  
                    async for msg in ws:  
                        if msg.type == aiohttp.WSMsgType.TEXT:  
                            new_msg = await self._process_message_to_server(msg, system_prompt)  
                            if new_msg is not None:  
                                await target_ws.send_str(new_msg)  
                        else:  
                            logger.error("Unexpected message type from client: %s", msg.type)  

                async def from_server_to_client():  
                    async for msg in target_ws:  
                        if msg.type == aiohttp.WSMsgType.TEXT:  
                            new_msg = await self._process_message_to_client(msg)  
                            if new_msg is not None:  
                                await ws.send_str(new_msg)  
                        else:  
                            logger.error("Unexpected message type from server: %s", msg.type)  

                try:  
                    await asyncio.gather(from_client_to_server(), from_server_to_client())  
                except ConnectionResetError:  
                    logger.error("ConnectionResetError occurred")  

  
    def attach_to_app(self, app: web.Application, handshake_path: str, realtime_path: str):  
        app.router.add_get(handshake_path, self.handshake_handler)  
        app.router.add_get(realtime_path, self._handler_with_session_key)  
    # def attach_to_app(self, app, path):  
    #     app.router.add_get(path, self._handler_with_session_key)  