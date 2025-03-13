#!/usr/bin/env python  
"""  
Updated realtime voice AI agent using semantic_kernel for standardization.  
Make sure to install semantic-kernel[realtime] along with your other dependencies.  
"""  
  
import os  
import asyncio  
import json  
import yaml  
import logging  
from enum import Enum  
from typing import Any, Callable, Optional  
import base64
from aiohttp import web  
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  
from azure.core.credentials import AzureKeyCredential  
from utility import detect_intent, SessionState  
from agents.tools.hotel_plugins import Hotel_Tools
from agents.tools.flight_plugins import Flight_Tools
from semantic_kernel.connectors.ai import FunctionChoiceBehavior

  
# Import Semantic Kernel classes  
from semantic_kernel import Kernel  
from semantic_kernel.connectors.ai.open_ai import (  
    AzureRealtimeExecutionSettings,  
    AzureRealtimeWebsocket,  
)  
from openai.types.beta.realtime import ResponseAudioTranscriptDoneEvent,ConversationItemInputAudioTranscriptionCompletedEvent
from semantic_kernel.connectors.ai.realtime_client_base import RealtimeClientBase

from semantic_kernel.contents import (  
    AudioContent,  
    RealtimeTextEvent,  
    RealtimeAudioEvent,  
     
    TextContent,  
)  
  
# Configure logging  
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")  
logger = logging.getLogger(__name__)  
  
  
# --------------------------- RTMiddleTier Class ---------------------------  
  
class RTMiddleTier:  
    # These properties are “server‑enforced” and/or stored locally  
    tools: dict[str, dict[str, Tool]] = {}  
    current_agent_tools: dict[str, Tool] = {}  
    model: Optional[str] = None  
    agents: list[dict] = []  
    agent_names: list[str] = []  
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
    session_state = SessionState()  # To backup the conversation state  
    
    # Semantic Kernel instance (for function calling, etc.)  
    kernel: Kernel  

    # Realtime connectivity parameters (for Azure realtime service)  
    deployment: str  
    endpoint: str  
    key: Optional[str] = None  
    use_classification_model: bool = True  

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):  
        # Initialize the Semantic Kernel  
        self.kernel = Kernel()

        # Load agent profiles and associated tools  
        self.load_agents()  
        self.hotel_tool = Hotel_Tools()
        self.flight_tool = Flight_Tools()
        if self.current_agent.get("name") == self.hotel_tool.agent_name:  
            self.kernel.add_plugin(plugin=self.hotel_tool, plugin_name="hotel_tools", description="tools for hotel agent")
        elif self.current_agent.get("name") == self.flight_tool.agent_name:
            self.kernel.add_plugin(plugin=self.flight_tool, plugin_name="flight_tools", description="tools for flight agent")


        self.endpoint = endpoint  
        self.deployment = deployment  
        if isinstance(credentials, AzureKeyCredential):  
            self.key = credentials.key  
        else:  
            self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")  
            self._token_provider()  # warm up token  

    def load_agents(self):  
        base_path = "agents/agent_profiles"  
        agent_profiles = [f for f in os.listdir(base_path) if f.endswith("_profile.yaml")]  
        with open("../../../data/user_profile.json") as f:  
            user_profile = json.load(f)  
        for profile in agent_profiles:  
            profile_path = os.path.join(base_path, profile)  
            with open(profile_path, "r") as file:  
                try:  
                    data = yaml.safe_load(file)  
                    data["persona"] = data["persona"].format(  
                        customer_name=user_profile["name"],  
                        customer_id=user_profile["customer_id"]  
                    )  
                    self.agents.append(data)  
                except yaml.YAMLError as exc:  
                    logger.error(f"Error loading {profile}: {exc}")  
        self.agent_names = [agent["name"] for agent in self.agents]  
        logger.info("Available agents: %s", self.agent_names)  
        self.current_agent = next(agent for agent in self.agents if agent.get("default_agent"))  


    async def _detect_intent_change(self):  
        extracted_history = [f"{item['item']['role']}: {item['item']['content'][0]['text']}" for item in self.history]  
        logger.info("Current agent: %s", self.current_agent.get("name"))  
        conversation = "\n".join(extracted_history)  
        intent = await detect_intent(conversation)  
        logger.info("Detected intent: %s", intent)  
        if intent in self.agent_names and intent != self.current_agent.get("name"):  
            self.target_agent_name = intent  
            logger.info("Switching to new agent: %s", self.target_agent_name)  
            self.transfer_conversation = True  
            

    async def _reinitialize_state(self, target_ws: AzureRealtimeWebsocket):
        logger.info("Cleared audio buffer")  
        await target_ws.send(RealtimeTextEvent(  
            service_type="input_audio_buffer.clear",  
            text=TextContent(text=""),

        ))  
        # if self.history:
        #     for item in self.history:
        #         await target_ws.send(item)

    async def _forward_messages(self, session_state_key: str, ws: web.WebSocketResponse):  
        logger.info("Starting Semantic Kernel based realtime session")  

        # Build the realtime session settings from current configuration.  
        settings = AzureRealtimeExecutionSettings(  
            instructions=self.current_agent.get("persona"),  
            turn_detection={"type": "server_vad", "threshold": 0.5, "prefix_padding_ms": 300, "silence_duration_ms": 200},  
            input_audio_transcription={"model": "whisper-1"},  
            input_audio_format="pcm16",
             output_audio_format="pcm16",
            voice="shimmer",  
            temperature=self.temperature,  
            max_response_output_tokens=self.max_tokens,  
            disable_audio=self.disable_audio,  
            function_choice_behavior=FunctionChoiceBehavior.Auto(),

        )  

        realtime_client = AzureRealtimeWebsocket()


        async with realtime_client(settings=settings, create_response=True, kernel=self.kernel):  
            # Task: forward messages from the client (ws) to the realtime service.  
            async def from_client_to_realtime():  
                async for msg in ws:  
                    if msg.type == web.WSMsgType.TEXT: 
                        try:  
                            message = json.loads(msg.data)  
                        except Exception as e:  
                            logger.error("Error parsing client message: %s", e)  
                            continue  
                        msg_type = message.get("type")  
                        # logger.info("sending message type: %s", msg_type) 


                        # Process session.update commands.  
                        if msg_type == "session.update":  
                            update_event = RealtimeTextEvent(  
                                text=TextContent(text="Session update received"),  
                            )  
                            await realtime_client.send(update_event)  

                        # Forward appended audio from the client.  
                        elif msg_type == "input_audio_buffer.append": 
                            audio_data = message.get("audio")
                            if audio_data:  
                                
                                audio_event = RealtimeAudioEvent(  
                                    audio=AudioContent(data=audio_data, data_format="base64")  
                                )  
                                await realtime_client.send(audio_event)  

                        # Forward clear-buffer commands.  
                        elif msg_type == "input_audio_buffer.clear":  
                            clear_event = RealtimeTextEvent(  
                                text=TextContent(text=""),  
                            )  
                            await realtime_client.send(clear_event)  
                        else:  
                            logger.warning("Unhandled client message type: %s", msg_type)  
                    else:  
                        logger.error("Unexpected message type from client: %s", msg.type)  

            # Task: forward events from the realtime service to the client.  
            async def from_realtime_to_client():  
                async for event in realtime_client.receive():  
                    try:  
                        if isinstance(event, RealtimeAudioEvent):  
                            audio_data = event.audio.data
                            audio_base64 = base64.b64encode(audio_data).decode('ascii')
                            await ws.send_json({  
                                "type": "response.audio.delta",  
                                "delta": audio_base64
                            })  
                        elif isinstance(event.service_event,ResponseAudioTranscriptDoneEvent):
                            print("Received response transcription.completed event" , event.service_event.transcript)
                            transcript = event.service_event.transcript
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

                        elif isinstance(event.service_event,ConversationItemInputAudioTranscriptionCompletedEvent):
                            print("Received input transcription.completed event" , event.service_event.transcript)
                            transcript = event.service_event.transcript
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

                        else:  
                            # For other events, convert any pydantic models to a dictionary.  
                            e_payload = event.service_event  
                            if hasattr(e_payload, "dict"):  
                                e_payload = e_payload.dict()  
                            await ws.send_json(e_payload)  
                    except Exception as e:  
                        logger.error("Error sending realtime event to client: %s", e)  
                    # If an agent change was triggered...  
                    if self.target_agent_name is not None:  
                        logger.info("detecting change of intent, cancelling current response")
                        await realtime_client.send(RealtimeTextEvent(  
                            service_type="response.cancel",  
                            text=TextContent(text=""),
                        ))  

                        # Update instructions dynamically when switching agents  
                        self.current_agent = next((agent for agent in self.agents if agent.get("name") == self.target_agent_name), None)
                        self.kernel.remove_all_services()
                        if self.current_agent.get("name") == self.hotel_tool.agent_name:  
                            self.kernel.add_plugin(plugin=self.hotel_tool, plugin_name="hotel_tools", description="tools for hotel agent")
                        elif self.current_agent.get("name") == self.flight_tool.agent_name:
                            self.kernel.add_plugin(plugin=self.flight_tool, plugin_name="flight_tools", description="tools for flight agent")
                        settings.instructions = self.current_agent.get("persona")  

                        await realtime_client.update_session(settings= settings, kernel=self.kernel, create_response=True)

                        self.transfer_conversation = False  
                        self.target_agent_name = None  
                        # await self._reinitialize_state(realtime_client)

                        await realtime_client.send(RealtimeTextEvent(  
                            text=TextContent(text=""),  
                            service_type="response.create",  
                        ))  
                        for item in self.history:  
                            await ws.send_json(item)  

            await asyncio.gather(from_client_to_realtime(), from_realtime_to_client())  
            # except Exception as e:  
            #     logger.error("Error in realtime message forwarding: %s", e)  
                # Optionally reinitialize session or take remedial action.  

    async def _websocket_handler(self, session_state_key: str, request: web.Request):  
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
        await self._forward_messages(session_state_key, ws)  
        return ws  

    def attach_to_app(self, app, path):  
        async def _handler_with_session_key(request: web.Request):  
            session_state_key = request.query.get("session_state_key", "default_session_id")  
            logger.info("Session state key: %s", session_state_key)  
            init_history = self.session_state.get(session_state_key)  
            if init_history:  
                logger.info("Retrieved session state with key: %s", session_state_key)  
                self.history = init_history  
            return await self._websocket_handler(session_state_key, request)  
        app.router.add_get(path, _handler_with_session_key)  