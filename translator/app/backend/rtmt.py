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
                session.system_prompt = f"""You are an AI translator designed to facilitate conversations between two people speaking {partner_lang} and {user_lang}. When someone speaks in {partner_lang}, translate to {user_lang}, and when someone speaks in {user_lang}, translate to {partner_lang}. Be a truthful translator, and do not add any information beyond what is being said."""  
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

    async def _process_message_to_client(self, msg: aiohttp.WSMessage) -> Optional[str]:  
        message = json.loads(msg.data)  
        updated_message = msg.data 
         
        if message is not None:  
            if "delta" not in message:  
                if message.get("type") == "error":  
                    logger.error(message)  
            match message.get("type"):  
                case "session.created":  
                    logger.debug("session created")  
                    session_info = message.get("session", {})  
                    session_info["instructions"] = ""  
                    session_info["tools"] = []  
                    session_info["tool_choice"] = "none"  
                    session_info["max_response_output_tokens"] = None  
                    updated_message = json.dumps(message)  
        return updated_message  

    async def _process_message_to_server(self, msg: aiohttp.WSMessage, system_prompt: str) -> Optional[str]:  
        message = json.loads(msg.data)  
        logger.debug("message type sent to server: %s", message.get("type"))  
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

    async def _client_message_handler(self, session_key: str, ws: web.WebSocketResponse):  
        """  
        For each connected client, this task listens for messages.  
        • If the message is an audio append, its base64–encoded audio is decoded and put into the shared queue.  
        • Otherwise, the message is processed and put into a common outgoing queue.  
        """  
        session = self.sessions[session_key]  
        async for msg in ws:  
            if msg.type == aiohttp.WSMsgType.TEXT:  
                try:  
                    message = json.loads(msg.data)  
                except Exception as e:  
                    logger.error("Invalid JSON message: %s", e)  
                    continue  
                if message.get("type") == "input_audio_buffer.append":  
                    # Decode and store the audio chunk (as raw bytes)  

                    try:  

                        audio_bytes = base64.b64decode(message.get("audio", ""))  
                        # logger.info("audio added to buffer")
                        await session.audio_queue.put(audio_bytes)  
                    except Exception as e:  
                        logger.error("Error decoding audio: %s", e)  
                else:  
                
                    processed_msg = await self._process_message_to_server(msg, session.system_prompt)  
                    if processed_msg is not None:  
                        await session.outgoing_queue.put(processed_msg)  
            else:  
                logger.error("Unexpected message type from client: %s", msg.type)  

    async def _azure_worker(self, session_key: str):  
        """  
        This background task opens one websocket connection to OpenAI via Azure  
        for the session. It has two loops:  
        • A send_loop that pulls messages (audio after mixing or other commands) from the outgoing queue  
        • A receive_loop that reads responses from the azure endpoint and pushes each response into  
        every client’s dedicated output queue.  
        """  
        session = self.sessions[session_key]  
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
                        msg_to_send = await session.outgoing_queue.get()  
                        await target_ws.send_str(msg_to_send)  
                async def receive_loop():  
                    async for msg in target_ws:  
                        if msg.type == aiohttp.WSMsgType.TEXT:  
                            processed = await self._process_message_to_client(msg)  
                            if processed is not None:  
                                # Push a copy of the processed message into each client’s output queue.  
                                for _, out_queue in session.client_output_queues.items():  
                                    try:  
                                        await out_queue.put(processed)  
                                    except Exception as e:  
                                        logger.error("Error putting message into client queue: %s", e)  
                        else:  
                            logger.error("Unexpected message type from Azure: %s", msg.type)  
                await asyncio.gather(send_loop(), receive_loop())  

    async def _mixer_loop(self, session_key: str):  
        """  
        This mixer runs on a fixed interval (here every 100ms). It drains all  
        available audio chunks from the shared queue, mixes them sample-by–sample using an average,  
        re-encodes the mixed result as base64, and then enqueues an audio append command.  
        """  
        logger.info("mixer started")    
        session = self.sessions[session_key]  
        mix_interval = 0.1  # seconds  
        while True:  
            await asyncio.sleep(mix_interval)  
            chunks = []  
            while not session.audio_queue.empty():  
                try:  
                    chunk = session.audio_queue.get_nowait()  
                    chunks.append(chunk)  
                except asyncio.QueueEmpty:  
                    break  
            if chunks:  
                mixed_bytes = mix_audio_buffers(chunks)  
                base64_audio = base64.b64encode(mixed_bytes).decode("ascii")  
                mixed_message = {  
                    "type": "input_audio_buffer.append",  
                    "audio": base64_audio,  
                }  
                json_message = json.dumps(mixed_message)  
                await session.outgoing_queue.put(json_message)  

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
    
        
        logger.info("session_key in _handler_with_session_key: %s", session_key)
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
        if len(session_key)==0:
            return ws
        session = self.sessions[session_key]  
        if not session.ready:
            return ws
 

        # Launch this client’s message handler (which constantly reads from its websocket)  
        asyncio.create_task(self._client_message_handler(session_key, ws))  

        session.client_language_mapping[client_id]= user_lang   
        # Create a dedicated output queue for this client.  
        session.client_output_queues[ws] = asyncio.Queue()  
        # Start the client’s output handler so that it reads from its output queue.  
        

        # Start the azure worker and audio mixer if this is the first connection.  
        if session.azure_task is None:  
            session.azure_task = asyncio.create_task(self._azure_worker(session_key))  
            session.mixer_task = asyncio.create_task(self._mixer_loop(session_key))  
        await self._client_output_handler(session_key,user_lang, ws)

        return ws  

    def attach_to_app(self, app: web.Application, handshake_path: str, realtime_path: str):  
        app.router.add_get(handshake_path, self.handshake_handler)  
        app.router.add_get(realtime_path, self._handler_with_session_key)  
    
