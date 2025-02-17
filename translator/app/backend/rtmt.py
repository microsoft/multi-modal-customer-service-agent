import os  
import aiohttp  
import asyncio  
import json  
import logging  
from enum import Enum  
from typing import Any, Callable, Optional  
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
    tools: dict[str, dict[str, Tool]] = {}  
  
    temperature: Optional[float] = None  
    max_tokens: Optional[int] = None  
    disable_audio: Optional[bool] = None  
  
    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):  
        self.endpoint = endpoint  
        self.deployment = deployment  
        self.key = credentials.key if isinstance(credentials, AzureKeyCredential) else None  
        self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default") if not self.key else None  
        self.system_prompt = """You are an AI translator to help translate conversations between two people speaking English and Vietnamese. When a person speaks English, you translate to Vietnamese, and when a person speaks Vietnamese, then translate to English."""  
  
    async def _process_message_to_server(self, msg: str, ws: web.WebSocketResponse) -> Optional[str]:  
        message = json.loads(msg.data)  
        updated_message = msg.data  
        if message is not None:  
            match message["type"]:  
                case "session.update":  
                    session = message["session"]  
                    session["instructions"] = self.system_prompt  
                    if self.temperature is not None:  
                        session["temperature"] = self.temperature  
                    if self.max_tokens is not None:  
                        session["max_response_output_tokens"] = self.max_tokens  
                    if self.disable_audio is not None:  
                        session["disable_audio"] = self.disable_audio  
                    updated_message = json.dumps(message)  
        return updated_message  
  
    async def _process_message_to_client(self, msg: str, ws: web.WebSocketResponse, target_ws: web.WebSocketResponse) -> Optional[str]:  
        message = json.loads(msg.data)  
        updated_message = msg.data  
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
  
    async def _forward_messages(self, ws: web.WebSocketResponse):  
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
                            new_msg = await self._process_message_to_server(msg, ws)  
                            if new_msg is not None:  
                                await target_ws.send_str(new_msg)  
                        else:  
                            logger.error("Unexpected message type from client: %s", msg.type)  
  
                async def from_server_to_client():  
                    async for msg in target_ws:  
                        if msg.type == aiohttp.WSMsgType.TEXT:  
                            new_msg = await self._process_message_to_client(msg, ws, target_ws)  
                            if new_msg is not None:  
                                await ws.send_str(new_msg)  
                        else:  
                            logger.error("Unexpected message type from server: %s", msg.type)  
  
                try:  
                    await asyncio.gather(from_client_to_server(), from_server_to_client())  
                except ConnectionResetError:  
                    logger.error("ConnectionResetError occurred")  
  
    async def _handler_with_session_key(self, request: web.Request):  
        session_key = request.query.get("session_state_key", "default")  
        lang = request.query.get("lang", "en")  
  
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
  
        try:  
            await self._forward_messages(ws)  
        finally:  
            await ws.close()  
  
        return ws  
  
    def attach_to_app(self, app, path):  
        app.router.add_get(path, self._handler_with_session_key)  