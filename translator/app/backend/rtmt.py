from __future__ import annotations
  
import os  
import aiohttp  
import asyncio  
import json  
import logging  
from typing import Any, Callable, Optional, Dict, List  
from aiohttp import web  
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  
from azure.core.credentials import AzureKeyCredential  
from utility import Session, mix_audio_buffers
import base64


  
# Configure logging  
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")  
logger = logging.getLogger(__name__)  
  
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
                partner_lang = [lang for lang in session.user_languages if lang != user_lang][0] if len(session.user_languages) > 1 else None  
                session.system_prompts = {
                    user_lang: f"""You are an AI translator who's sole function is to translate what you hear in {user_lang} to {partner_lang}. Be a truthful translator, and do not add any information beyond what is being said. **Never** respond with anything except the translation of what you heard.""",
                    partner_lang: f"""You are an AI translator who's sole function is to translate what you hear in {partner_lang} to {user_lang}. Be a truthful translator, and do not add any information beyond what is being said. **Never** respond with anything except the translation of what you heard."""
                }
                logger.info("joining, my lang: %s, partner_lang: %s", user_lang, partner_lang)  
                session.ready = True
                return web.json_response({"status": "ok", "session_key": session_key, "ready": True, "partner_lang": partner_lang})  
        elif action == "status":  
            session_key = request.query.get("session_key")  
            if not session_key:  
                return web.json_response({"status": "error", "error": "Missing session_key"}, status=400)  
            async with self.session_lock:  
                if session_key not in self.sessions:  
                    return web.json_response({"status": "error", "error": "Invalid session_key"}, status=404)  
                session = self.sessions[session_key]  
                partner_lang = [lang for lang in session.user_languages if lang != user_lang][0] if len(session.user_languages) > 1 else None  
                if partner_lang is None:  
                    is_ready = False  
                    status = "ok"  
                else:  
                    is_ready = True  
                    status = "ok"  
                logger.debug("status polling, my lang: %s, partner_lang: %s", user_lang, partner_lang)  
                return web.json_response({"status": status, "session_key": session_key, "ready": is_ready, "partner_lang": partner_lang})  
        else:  
            return web.json_response({"status": "error", "error": "Invalid action"}, status=400)  

    async def _process_message_to_client(self, msg: aiohttp.WSMessage, client_id: str) -> Optional[str]:  
        message = json.loads(msg.data)  
        updated_message = msg.data 
         
        if message is not None:  
            if "delta" not in message:  
                if message.get("type") == "error":  
                    logger.error(message)  
            match message.get("type"):  
                case "session.created":  
                    logger.info("session created")  
                    session_info = message.get("session", {})  
                    session_info["instructions"] = ""  
                    session_info["tools"] = []  
                    session_info["tool_choice"] = "none"  
                    session_info["max_response_output_tokens"] = None  
                    updated_message = json.dumps(message)  
                case "conversation.item.input_audio_transcription.completed":
                    logger.info("Client: %s, Input audio transcript: %s", client_id, message.get("transcript"))
                case "response.audio_transcript.done":
                    logger.info("Client: %s, Output audio transcript %s", client_id, message.get("transcript"))
        return updated_message  

    async def _process_message_to_server(self, msg: aiohttp.WSMessage, system_prompt: str, client_id: str) -> Optional[str]:  
        try:  
            message = json.loads(msg.data)  
        except Exception as e:  
            logger.error("Invalid JSON message: %s", e)   
        updated_message = msg.data  
        if message is not None:  
            match message.get("type"):  
                case "session.update":  
                    session_info = message.get("session", {})  
                    session_info["instructions"] = system_prompt  
                    if self.temperature is not None:  
                        session_info["temperature"] = self.temperature  
                    if self.max_tokens is not None:  
                        session_info["max_response_output_tokens"] = self.max_tokens  
                    if self.disable_audio is not None:  
                        session_info["disable_audio"] = self.disable_audio  
                    updated_message = json.dumps(message)  
                    logger.info("Client: %s, Session updated: %s", client_id, updated_message)
        return updated_message  
    async def _client_output_handler(self, session_key: str,user_lang:str, ws: web.WebSocketResponse):  
        """  
        This task is spawned for each client.  
        It reads from the client’s dedicated output queue (responses buffered from OpenAI)  
        and sends those messages back to the client.  
        """  
        session = self.sessions[session_key]  
        client_queue = session.client_output_queues.get(ws)  
        if client_queue is None:  
            logger.error("No output queue found for client")  
            return  
        try:  
            while True:  
                message = await client_queue.get()  
                logger.debug("message sent back to client with language %s", user_lang)
                await ws.send_str(message)  
        except asyncio.CancelledError:  
            logger.debug("Output handler for client cancelled")  
        except Exception as e:  
            logger.error("Error in client output handler: %s", e)  

    async def _client_message_handler(self, session_key: str, ws: web.WebSocketResponse, client_id: str):  
        """  
        For each connected client, this task listens for messages.  
        • If the message is an audio append, its base64–encoded audio is decoded and put into the shared queue.  
        • Otherwise, the message is processed and put into a common outgoing queue.  
        """  
        session = self.sessions[session_key]  
        user_lang = session.client_language_mapping[client_id]
        system_prompt = session.system_prompts[user_lang]
        async for msg in ws:  
            if msg.type == aiohttp.WSMsgType.TEXT:            
                processed_msg = await self._process_message_to_server(msg, system_prompt, client_id)  
                if processed_msg is not None:  
                    await session.client_to_realtime_queues[ws].put(processed_msg) 
            else:  
                logger.error("Unexpected message type from client: %s", msg.type)  

    async def _azure_worker_for_client(self, session_key: str, ws: web.WebSocketResponse):  
        """  
        This background task opens a websocket connection to OpenAI via Azure per client  
        for the session. It has two loops:  
        • A send_loop that pulls messages from the outgoing queue  
        • A receive_loop that reads responses from the azure endpoint and pushes each response into  
        the appropriate client’s dedicated output queue.  
        """  
        session = self.sessions[session_key] 
        client_id = session.client_id_mapping.get(ws, "unknown") 
        params = {"api-version": "2024-10-01-preview", "deployment": self.deployment}  
        headers = {}  
        if self.key is not None:  
            headers = {"api-key": self.key}  
        else:  
            headers = {"Authorization": f"Bearer {self._token_provider()}"}  
        async with aiohttp.ClientSession(base_url=self.endpoint) as client_session:  
            async with client_session.ws_connect("/openai/realtime", headers=headers, params=params) as target_ws:  
                async def send_loop():  
                    while True:  
                        msg_to_send = await session.client_to_realtime_queues[ws].get()
                        await target_ws.send_str(msg_to_send)  
                async def receive_loop():  
                    async for msg in target_ws:  
                        if msg.type == aiohttp.WSMsgType.TEXT:  
                            processed = await self._process_message_to_client(msg, client_id)  
                            if processed is not None: 
                                # Instead of sending back to the same client, send to the partner's output queue.
                                partner_ws = session.partner_mapping.get(ws)
                                if partner_ws in session.client_output_queues:
                                    try:
                                        await session.client_output_queues[partner_ws].put(processed)
                                    except Exception as e:  
                                        logger.error("Error putting message into client queue: %s", e)
                                else:
                                    logger.warning("No partner found for this client")
                        else:  
                            logger.error("Unexpected message type from Azure: %s", msg.type)  
                await asyncio.gather(send_loop(), receive_loop())  


    async def _handler_with_session_key(self, request: web.Request):  
        """  
        When a client connects on the /realtime endpoint it:  
        • Gets added to the session's list of clients.  
        • (If not already running) starts the azure worker and mixer tasks.  
        • Starts a per-client task to receive incoming messages.  
        """  
        session_key = request.query.get("session_key") 
        user_lang = request.query.get("user_lang") 
        client_id = request.query.get("client_id")
    
        
        #logger.info("session_key in _handler_with_session_key: %s", session_key)
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
        if len(session_key)==0:
            return ws
        session = self.sessions[session_key]  
        if not session.ready:
            return ws

        # Launch this client’s message handlers
        asyncio.create_task(self._client_message_handler(session_key, ws, client_id))  
        session.azure_workers[ws] = asyncio.create_task(self._azure_worker_for_client(session_key, ws))
        

        # Save languange and dedicated queues for this client.
        session.client_language_mapping[client_id]= user_lang   
        session.client_id_mapping[ws] = client_id
        session.client_output_queues[ws] = asyncio.Queue()  
        session.client_to_realtime_queues[ws] = asyncio.Queue()
        
        # Create partner mapping for the clients once both are connected
        if len(session.client_output_queues) == 2:
            existing_ws = next(iter(session.client_output_queues.keys()))
            session.partner_mapping[ws] = existing_ws
            session.partner_mapping[existing_ws] = ws
        
        await self._client_output_handler(session_key, user_lang, ws)

        return ws  

    def attach_to_app(self, app: web.Application, handshake_path: str, realtime_path: str):  
        app.router.add_get(handshake_path, self.handshake_handler)  
        app.router.add_get(realtime_path, self._handler_with_session_key)  
    
