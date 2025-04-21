import os
import aiohttp
import asyncio
import json
import yaml
from enum import Enum
from typing import Any, Callable, Optional
from aiohttp import web
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from utility import detect_intent, SessionState
import logging  
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
    tools: dict[str, dict[str, Tool]] = {}
    current_agent_tools: dict[str, Tool] = {}
    # Server-enforced configuration, if set, these will override the client's configuration
    # Typically at least the model name and system message will be set by the server
    model: Optional[str] = None
    agents: Optional[list[dict]] = []
    agent_names: Optional[list[str]] = []
    current_agent: Optional[dict] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    disable_audio: Optional[bool] = None
    max_history_length = 3
    _tools_pending = {}
    _token_provider = None
    transfer_conversation = False
    target_agent_name = None
    history = []
    init_user_question = None
    session_state = SessionState() #to backup the state of the conversation

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):
        self.load_agents()
        self.load_agent_tools()
        self.endpoint = endpoint
        self.deployment = deployment
        if isinstance(credentials, AzureKeyCredential):
            self.key = credentials.key
        else:
            self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")
            self._token_provider() # Warm up during startup so we have a token cached when the first request arrives
        # init_history = self.session_state.get(self.session_state_key)
        # if init_history:
        #     self.history = init_history
    
    def load_agents(self):
        base_path = "agents/agent_profiles"  
        agent_profiles = [f for f in os.listdir(base_path) if f.endswith("_profile.yaml")]
        # Load user profile to personalize the agent persona
        with open('../../../data/user_profile.json') as f:
            user_profile = json.load(f)
        for profile in agent_profiles:
            profile_path = os.path.join(base_path, profile)
            with open(profile_path, 'r') as file:
                try:
                    data = yaml.safe_load(file)
                    data['persona'] = data['persona'].format(customer_name =user_profile['name'], customer_id=user_profile['customer_id'])
                    self.agents.append(data)
                except yaml.YAMLError as exc:
                    logger.error(f"Error loading {profile}: {exc}")  
        self.agent_names = [agent['name'] for agent in self.agents]
        logger.info("Available agents: %s", self.agent_names)  
        self.current_agent = next(agent for agent in self.agents if agent['default_agent'])
    
    def load_agent_tools(self):
        from agents.tools.hotel_tools import hotel_tools
        from agents.tools.flight_tools import flight_tools

        agent_tools = {
            'hotel_agent': hotel_tools,
            'flight_agent': flight_tools
        }

        self.attach_tools(agent_tools)

    def attach_tools(self, agent_tools: dict[str, dict[str, Callable]]):
        for agent in self.agents:
            agent_name = agent.get('name')
            self.tools[agent_name] = {}
            for tool in agent.get('tools', []):
                tool_name = tool['name']
                tool_schema = {  
                    "type": tool['type'],  
                    "name": tool['name'],  
                    "description": tool['description'],  
                    "parameters": tool['parameters']  
                }  
                self.tools[agent_name][tool_name] = Tool(schema=tool_schema, target=agent_tools[agent_name][tool_name])
        self.set_current_agent_tools()

    def set_current_agent_tools(self):
        self.current_agent_tools = self.tools[self.current_agent.get('name')]

    async def _detect_intent_change(self):  
        # Use the accumulated history for intent detection
        extracted_history = [f"{item['item']['role']}: {item['item']['content'][0]['text']}" for item in self.history]
        logger.info("Current agent: %s", self.current_agent.get('name'))  
        conversation = "\n".join(extracted_history)  
        intent = await detect_intent(conversation) 
        logger.info("Detected intent: %s", intent)  
        if intent in self.agent_names and intent != self.current_agent.get('name'):  
            self.target_agent_name = intent
            logger.info("Switching to new agent: %s", self.target_agent_name)  
            self.transfer_conversation = True  

            

    async def _attach_instruction(self, server_ws):
        server_msg = {  
            "type": "session.update",  
            "session": {  
                "turn_detection": {  
                    "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 200

                },
                "input_audio_transcription": {
                "model": "whisper-1"
                
            }
            }  
        }  
        session = server_msg["session"]
        if self.current_agent.get('persona') is not None:
            session["instructions"] = self.current_agent.get('persona')
        if self.temperature is not None:
            session["temperature"] = self.temperature
        if self.max_tokens is not None:
            session["max_response_output_tokens"] = self.max_tokens
        if self.disable_audio is not None:
            session["disable_audio"] = self.disable_audio
        session["tool_choice"] = "auto" if len(self.tools) > 0 else "none"
        session["tools"] = [tool.schema for tool in self.current_agent_tools.values()]
        # new_msg = await self._process_message_to_server(new_msg, ws)

        await server_ws.send_json(server_msg)

    async def _process_message_to_client(self, session_state_key: str, msg: str, client_ws: web.WebSocketResponse, server_ws: web.WebSocketResponse) -> Optional[str]:
        message = json.loads(msg.data)
        updated_message = msg.data
        if message is not None:
            if "delta" not in message:
                if message["type"]=="error":
                    logger.error(message)
            match message["type"]:
                case "session.created":
                    logger.info("session created")
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
                        
                    if message["item"]["type"] == "function_call":
                        if  message["item"]["name"]=="transfer_conversation":
                            logger.info("detecting transfer_conversation in function calling")
                            if not self.use_classification_model:
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
                        try:
                            item = message["item"]
                            tool_call = self._tools_pending[message["item"]["call_id"]]
                            tool = self.current_agent_tools[item["name"]]
                            args = item["arguments"]
                            args= json.loads(args)
                            if item["name"]=="get_information_from_camera":
                                logger.info("detecting get_information_from_camera function calling")
                                #get last n frames from session state
                                frames = self.session_state.get(f"{session_state_key}_video")
                                if frames:
                                    args["base64_encoded_data"] = frames
                                else:
                                    logger.error("No video frames found in session state")  

                            result = await tool.target(args)
                            
                        except Exception as e:
                            logger.error("Error in tool call: %s", str(e))
                            result = ToolResult(f"encountered this error, {str(e)},\n, just siliently retry a couple of times before apologizing to the customer", ToolResultDirection.TO_SERVER)
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
                    if "response" in message:
                        replace = False
                        for i, output in enumerate(reversed(message["response"]["output"])):
                            if output["type"] == "function_call":
                                try:
                                    message["response"]["output"].pop(i) 
                                    replace = True 
                                except IndexError:
                                    logger.error("IndexError %s",  message["response"]["output"])
                                
                        if replace:
                            updated_message = json.dumps(message)    
                case "conversation.item.input_audio_transcription.completed":
                    ## add logic to detect intent change
                    transcript = message.get("transcript","")
                    if len(transcript) > 0:
                        self.history.append({
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
                            })
                        # todo: extend the conversation history when transfer conversation so that next agent has more context. Last request might not be sufficient
                        # Trigger intent detection
                        if self.use_classification_model:   
                            asyncio.create_task(self._detect_intent_change())  

                    # Retain only the last n turnss  
                    if len(self.history) > self.max_history_length:  
                        self.history.pop(0)  
                    # Back up the updated history  
                    self.session_state.set(session_state_key, self.history)  

                case "response.audio_transcript.done":
                    ## add logic to detect intent change
                    transcript = message.get("transcript","")
                    self.history.append({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "status": "completed",
                            "role": "assistant",
                            "content": [{
                            "type": "text",
                            "text": f"{transcript}"
                            }]
                        }
                        })

                    # Retain only the last n turns
                    self.history = self.history[-self.max_history_length:]
                    self.session_state.set(session_state_key, self.history)
    
                    # Back up the updated history  
                    self.session_state.set(session_state_key, self.history)  

        return updated_message

    async def _process_message_to_server(self, msg: str, ws: web.WebSocketResponse) -> Optional[str]:
        message = json.loads(msg.data)    
        server_trigger = False        
        updated_message = msg.data
        if message is not None:

            match message["type"]:
                case "session.update":
                    session = message["session"]
                    if self.current_agent.get('persona') is not None:
                        session["instructions"] = self.current_agent.get('persona')
                    if self.temperature is not None:
                        session["temperature"] = self.temperature
                    if self.max_tokens is not None:
                        session["max_response_output_tokens"] = self.max_tokens
                    if self.disable_audio is not None:
                        session["disable_audio"] = self.disable_audio
                    session["tool_choice"] = "auto" if len(self.tools) > 0 else "none"
                    session["tools"] = [tool.schema for tool in self.current_agent_tools.values()]
                    updated_message = json.dumps(message)
                case "conversation.item.create":
                    server_trigger = True

        return server_trigger, updated_message
    async def _reinitialize_state(self, target_ws: web.WebSocketResponse):
        logger.info("cancelling current response")
        await target_ws.send_json({"type": "response.cancel"})
        logger.info("Reinitializing session state")  
        server_msg = {"type":"input_audio_buffer.clear"}
        logger.info("Cleared audio buffer")  
        await target_ws.send_json(server_msg)
        await self._attach_instruction(target_ws)
        if self.history:
            for item in self.history:
                await target_ws.send_json(item)


    async def _forward_messages(self, session_state_key: str, ws: web.WebSocketResponse):
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
                            server_trigger, new_msg = await self._process_message_to_server(msg, ws)
                            if new_msg is not None:
                                await target_ws.send_str(new_msg)
                                if server_trigger:
                                    logger.info("triggering model's response from text")
                                    await target_ws.send_json({'type': 'response.create', 'response':{'modalities': ['audio', 'text'],'conversation':'none', 'input': [{'type': 'message', 'role':'user', 'content':[{'type':'input_text', 'text': 'ask him how he is doing'}]}]}})
                        else:
                            logger.error("Unexpected message type from client: %s", msg.type)  

                async def from_server_to_client():
                    async for msg in target_ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            new_msg = await self._process_message_to_client(session_state_key, msg, ws, target_ws)
                            
                            if new_msg is not None and self.target_agent_name is None:

                                await ws.send_str(new_msg)
                            else:
                                if self.target_agent_name is not None:

                                    self.current_agent = next((agent for agent in self.agents if agent.get('name') == self.target_agent_name), None)
                                    self.set_current_agent_tools()
                                    self.transfer_conversation = False
                                    self.target_agent_name = None
                                    await self._reinitialize_state(target_ws)

                                    await target_ws.send_json({'type': 'response.create'})


                        else:
                            logger.error("Unexpected message type from server: %s", msg.type)  

                try:
                    await asyncio.gather(from_client_to_server(), from_server_to_client())
                except ConnectionResetError:
                    logger.error("ConnectionResetError occurred")  
                    await self._reinitialize_state(target_ws)

    async def _websocket_handler(self,session_state_key:str, request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self._forward_messages(session_state_key, ws)
        return ws
    
    def attach_to_app(self, app, path):
        async def _handler_with_session_key(request: web.Request):
            # Extract session_state_key from query parameter (use a default if not provided)
            session_state_key = request.query.get("session_state_key", "default_session_id")
            logger.info("Session state key: %s", session_state_key)  
            # Pull any existing conversation history
            init_history = self.session_state.get(session_state_key)
            if init_history:
                logger.info("Retrieved session state with key: %s", session_state_key)  
                self.history = init_history
            return await self._websocket_handler(session_state_key, request)
        app.router.add_get(path, _handler_with_session_key)
