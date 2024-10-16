import aiohttp
import asyncio
import json
from enum import Enum
from typing import Any, Callable, Optional
from aiohttp import web
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from utility import detect_intent_change
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

class RTToolCall:
    tool_call_id: str
    previous_id: str

    def __init__(self, tool_call_id: str, previous_id: str):
        self.tool_call_id = tool_call_id
        self.previous_id = previous_id

class RTMiddleTier:
    endpoint: str
    deployment: str
    key: Optional[str] = None
    use_classification_model: bool = True
    
    # Tools are server-side only for now, though the case could be made for client-side tools
    # in addition to server-side tools that are invisible to the client
    tools: dict[str, Tool] = {}

    # Server-enforced configuration, if set, these will override the client's configuration
    # Typically at least the model name and system message will be set by the server
    model: Optional[str] = None
    system_message: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    disable_audio: Optional[bool] = None
    backup_system_message: Optional[str] = None
    backup_tools: dict[str, Tool] = {}
    max_history_length = 5
    _tools_pending = {}
    _token_provider = None
    transfer_conversation = False
    history = []
    init_user_question = None

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):
        self.endpoint = endpoint
        self.deployment = deployment
        if isinstance(credentials, AzureKeyCredential):
            self.key = credentials.key
        else:
            self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")
            self._token_provider() # Warm up during startup so we have a token cached when the first request arrives
    async def _detect_intent_change(self):  
        # Use the accumulated history for intent detection  
        conversation = "\n".join(self.history)  
        job_description = self.system_message  
        print("starting intent detection")
  
        intent = await detect_intent_change(job_description, conversation)  
        print("intent: ", intent)
          
        if "yes" in intent:  # Adjust condition based on actual response  
            self.transfer_conversation = True  

            

    async def _attach_instruction(self, server_ws):
        message = {"type": "session.update", "session": {"instructions": self.system_message,"tools":[tool.schema for tool in self.tools.values()], "tool_choice": "auto" if len(self.tools) > 0 else "none"}}
        await server_ws.send_json(message)

    async def _process_message_to_client(self, msg: str, client_ws: web.WebSocketResponse, server_ws: web.WebSocketResponse) -> Optional[str]:
        message = json.loads(msg.data)
        updated_message = msg.data
        if message is not None:
            if "delta" not in message:
                print("message type\n", message["type"])
                if message["type"]=="error":
                    print(message)
            if "item" in message:
                print("item type\n", message["item"]["type"])
            if message.get("transcript"):
                print(message.get("transcript"))
            match message["type"]:
                case "session.created":
                    session = message["session"]
                    # Hide the instructions, tools and max tokens from clients, if we ever allow client-side 
                    # tools, this will need updating
                    session["instructions"] = ""
                    session["tools"] = []
                    session["tool_choice"] = "none"
                    session["max_response_output_tokens"] = None
                    updated_message = json.dumps(message)
                    await self._attach_instruction(server_ws)

                case "response.output_item.added":
                        
                    if (not self.use_classification_model) and "item" in message and message["item"]["type"] == "function_call":
                        if message["item"]["name"]=="transfer_conversation":
                            print("detecting transfer_conversation in function calling")
                            self.transfer_conversation = True

                        updated_message = None

                case "conversation.item.created":
                    if "item" in message and message["item"]["type"] == "function_call":
                        item = message["item"]
                        if item["call_id"] not in self._tools_pending:
                            self._tools_pending[item["call_id"]] = RTToolCall(item["call_id"], message["previous_item_id"])
                        updated_message = None
                    elif "item" in message and message["item"]["type"] == "function_call_output":
                        updated_message = None

                case "response.function_call_arguments.delta":
                    # if self.transfer_conversation:
                    #     self.cancel_response = True
                

                    updated_message = None
                
                case "response.function_call_arguments.done":
                    # if not self.use_classification_model:

    
                    
                    updated_message = None

                case "response.output_item.done":
                    if "item" in message and message["item"]["type"] == "function_call":
                        item = message["item"]
                        tool_call = self._tools_pending[message["item"]["call_id"]]
                        tool = self.tools[item["name"]]
                        args = item["arguments"]
                        result = await tool.target(json.loads(args))
                        await server_ws.send_json({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": item["call_id"],
                                "output": result.to_text() if result.destination == ToolResultDirection.TO_SERVER else ""
                            }
                        })
                        if result.destination == ToolResultDirection.TO_CLIENT:
                            # TODO: this will break clients that don't know about this extra message, rewrite 
                            # this to be a regular text message with a special marker of some sort
                            await client_ws.send_json({
                                "type": "extension.middle_tier_tool_response",
                                "previous_item_id": tool_call.previous_id,
                                "tool_name": item["name"],
                                "tool_result": result.to_text()
                            })
                        updated_message = None

                case "response.done":
                    if len(self._tools_pending) > 0:
                        response_create = {
                            "type": "response.create"
                        }
                        self._tools_pending.clear() # Any chance tool calls could be interleaved across different outstanding responses?
                        await server_ws.send_json(response_create)
                        print("send response create after tool calling")
                    if "response" in message:
                        replace = False
                        for i, output in enumerate(reversed(message["response"]["output"])):
                            if output["type"] == "function_call":
                                try:
                                    message["response"]["output"].pop(i) 
                                    replace = True 
                                except IndexError:
                                    print("IndexError",  message["response"]["output"])
                                
                        if replace:
                            updated_message = json.dumps(message)    
                case "conversation.item.input_audio_transcription.completed":
                    ## add logic to detect intent change
                    transcript = message.get("transcript","")
                    print("user transcript: ", transcript)
                    if len(transcript) > 0:
                        self.history.append("customer: "+ transcript)  
                        last_user_request= {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "status": "completed",
                                "role": "user",
                                "content": [{
                                "type": "input_text",
                                "text": f"{transcript}"
                                }]
                            }
                            }

                        self.init_user_question = last_user_request
                        # Trigger intent detection
                        if self.use_classification_model:   
                            asyncio.create_task(self._detect_intent_change())  

                    # Retain only the last n turns  
                    if len(self.history) > self.max_history_length:  
                        self.history.pop(0)  

                case "response.audio_transcript.done":
                    ## add logic to detect intent change
                    transcript = message.get("transcript","")
                    print("assistant transcript: ", transcript)
                    self.history.append("agent: "+ transcript)  
                    # Retain only the last n turns  
                    if len(self.history) > self.max_history_length:  
                        self.history.pop(0)  
    

        return updated_message

    async def _process_message_to_server(self, msg: str, ws: web.WebSocketResponse) -> Optional[str]:
        message = json.loads(msg.data)            
        updated_message = msg.data
        if message is not None:

            match message["type"]:
                case "session.update":
                    session = message["session"]
                    if self.system_message is not None:
                        session["instructions"] = self.system_message
                        # print("updated system message: ", session["instructions"])
                    if self.temperature is not None:
                        session["temperature"] = self.temperature
                    if self.max_tokens is not None:
                        session["max_response_output_tokens"] = self.max_tokens
                    if self.disable_audio is not None:
                        session["disable_audio"] = self.disable_audio
                    session["tool_choice"] = "auto" if len(self.tools) > 0 else "none"
                    session["tools"] = [tool.schema for tool in self.tools.values()]
                    updated_message = json.dumps(message)

        return updated_message

    async def _forward_messages(self, ws: web.WebSocketResponse):
        async with aiohttp.ClientSession(base_url=self.endpoint) as session:
            params = { "api-version": "2024-10-01-preview", "deployment": self.deployment }
            headers = {}
            if "x-ms-client-request-id" in ws.headers:
                headers["x-ms-client-request-id"] = ws.headers["x-ms-client-request-id"]
            if self.key is not None:
                headers = { "api-key": self.key }
            else:
                headers = { "Authorization": f"Bearer {self._token_provider()}" } # NOTE: no async version of token provider, maybe refresh token on a timer?
            async with session.ws_connect("/openai/realtime", headers=headers, params=params) as target_ws:
                async def from_client_to_server():
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            new_msg = await self._process_message_to_server(msg, ws)
                            if new_msg is not None:
                                await target_ws.send_str(new_msg)
                        else:
                            print("Error: unexpected message type:", msg.type)

                async def from_server_to_client():
                    async for msg in target_ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            # if self.cancel_response:
                                # print("cancelling response after user transfer")
                                # await target_ws.send_json({"type": "response.cancel"})
                                # self.cancel_response = False

                            new_msg = await self._process_message_to_client(msg, ws, target_ws)
                            
                            if new_msg is not None and not self.transfer_conversation:

                                await ws.send_str(new_msg)
                            else:
                                if self.transfer_conversation and self.init_user_question:
                                    server_msg = {  
                                        "type": "session.update",  
                                        "session": {  
                                            "turn_detection": {  
                                                "type": "server_vad"  
                                            },  
                                            "input_audio_transcription": {  
                                                "model": "whisper-1"  
                                            }  
                                        }  
                                    }  

                                    temp_system_message = self.system_message
                                    self.system_message = self.backup_system_message
                                    self.backup_system_message = temp_system_message
                                    temp_tools = self.tools
                                    self.tools = self.backup_tools
                                    self.backup_tools = temp_tools
                                    self.transfer_conversation = False
                                    print("cancelling current response")
                                    await target_ws.send_json({"type": "response.cancel"})
                                    session = server_msg["session"]
                                    if self.system_message is not None:
                                        session["instructions"] = self.system_message
                                    if self.temperature is not None:
                                        session["temperature"] = self.temperature
                                    if self.max_tokens is not None:
                                        session["max_response_output_tokens"] = self.max_tokens
                                    if self.disable_audio is not None:
                                        session["disable_audio"] = self.disable_audio
                                    session["tool_choice"] = "auto" if len(self.tools) > 0 else "none"
                                    session["tools"] = [tool.schema for tool in self.tools.values()]
                                    # new_msg = await self._process_message_to_server(new_msg, ws)
                                    await target_ws.send_json(server_msg)
                                    print("updated system session with new tools and system message")
                                    server_msg = {"type":"input_audio_buffer.clear"}
                                    print("clearing audio buffer after user transfer")
                                    await target_ws.send_json(server_msg)
                                    print("re-initiating user question")
                                    await target_ws.send_json(self.init_user_question)
                                    print("response create for conversation")

                                    await target_ws.send_json({'type': 'response.create'})

                                    # print("push the model to talk")

                                    # push_message =  {
                                    # "type": "conversation.item.create"
                                    # }
                                    # await target_ws.send_json(push_message)


                                    # print("trigger response from server")
                                    # await target_ws.send_json({  
                                    #     "type": "response.create"  
                                    # })  


                        else:
                            print("Error: unexpected message type:", msg.type)

                try:
                    await asyncio.gather(from_client_to_server(), from_server_to_client())
                except ConnectionResetError:
                    # Ignore the errors resulting from the client disconnecting the socket
                    pass

    async def _websocket_handler(self, request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self._forward_messages(ws)
        return ws
    
    def attach_to_app(self, app, path):
        app.router.add_get(path, self._websocket_handler)