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
    TurnDetection  
)  
from openai.types.beta.realtime import (
    ResponseAudioTranscriptDoneEvent,
    ConversationItemInputAudioTranscriptionCompletedEvent
)
from semantic_kernel.contents import (  
    AudioContent,  
    RealtimeTextEvent,  
    RealtimeAudioEvent,  
    RealtimeEvent,
    TextContent,  
)  
  
# Configure logging  
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")  
logger = logging.getLogger(__name__)  
  
  
# --------------------------- RTMiddleTier Class ---------------------------  
  
class RTMiddleTier:  
    model: Optional[str] = None  
    agents: list[dict] = []  
    agent_names: list[str] = []  
    current_agent: Optional[dict] = None  
    temperature: Optional[float] = None  
    max_tokens: Optional[int] = None  
    disable_audio: Optional[bool] = None  
    max_history_length = 3   
    _token_provider = None  
    transfer_conversation = False  
    target_agent_name = None  
    history = []  
    init_user_question = None  
    session_state = SessionState()  # To backup the conversation state
    realtime_settings: AzureRealtimeExecutionSettings = None  
    
    # Semantic Kernel instances (for function calling, etc.)  
    kernels: dict[str, Kernel] = {}
    current_agent_kernel: Optional[Kernel] = None  

    # Realtime connectivity parameters (for Azure realtime service)  
    deployment: str  
    endpoint: str  
    key: Optional[str] = None  
    use_classification_model: bool = True  

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):  
        # Initialize the Semantic Kernel  
        self.kernel = Kernel()

        # Load agent profiles and associated tools  
        self._load_agents()  
        self.endpoint = endpoint  
        self.deployment = deployment  
        if isinstance(credentials, AzureKeyCredential):  
            self.key = credentials.key  
        else:  
            self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")  
            self._token_provider()  # warm up token  

    def _load_agents(self):  
        base_path = "agents/agent_profiles"  
        agent_profiles = [f for f in os.listdir(base_path) if f.endswith("_profile.yaml")]  
        with open("../data/user_profile.json") as f:  
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
                    agent_name = data.get("name")
                    self.kernels[agent_name] = Kernel()
                    if agent_name == "hotel_agent":
                        self.kernels[agent_name].add_plugin(plugin=Hotel_Tools(), plugin_name="hotel_tools", description="tools for hotel agent")
                    elif agent_name == "flight_agent":
                        self.kernels[agent_name].add_plugin(plugin=Flight_Tools(), plugin_name="flight_tools", description="tools for flight agent")
                except yaml.YAMLError as exc:  
                    logger.error(f"Error loading {profile}: {exc}")  
        self.agent_names = [agent["name"] for agent in self.agents]  
        logger.info("Available agents: %s", self.agent_names)  
        self.current_agent = next(agent for agent in self.agents if agent.get("default_agent"))
        self.current_agent_kernel = self.kernels.get(self.current_agent.get("name"))  


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
            

    async def _reinitialize_session(self, realtime_client: AzureRealtimeWebsocket): 
        await realtime_client.send(RealtimeEvent(service_type="input_audio_buffer.clear"))  
        
        # Update instructions dynamically when switching agents  
        self.current_agent = next((agent for agent in self.agents if agent.get("name") == self.target_agent_name), None)
        self.current_agent_kernel = self.kernels.get(self.current_agent.get("name"))
        self.realtime_settings.instructions = self.current_agent.get("persona")  

        await realtime_client.update_session(settings=self.realtime_settings, kernel=self.current_agent_kernel)

        self.transfer_conversation = False  
        self.target_agent_name = None


    async def _forward_messages(self, session_state_key: str, ws: web.WebSocketResponse):  
        logger.info("Starting Semantic Kernel based realtime session")  

        # Build the realtime session settings from current configuration.  
        self.realtime_settings = AzureRealtimeExecutionSettings(  
            instructions=self.current_agent.get("persona"),  
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=200,
                create_response=False
            ),
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


        async with realtime_client(settings=self.realtime_settings, kernel=self.current_agent_kernel):  
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


                        # Client session.update commands are unused.  
                        if msg_type == "session.update":  
                            pass

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
                            clear_event = RealtimeEvent(  
                                service_type="input_audio_buffer.clear",  
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
                            logger.info("Received response transcription.completed event: %s", event.service_event.transcript)
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

                        elif isinstance(event.service_event,ConversationItemInputAudioTranscriptionCompletedEvent):
                            logger.info("Received input transcription.completed event: %s", event.service_event.transcript)
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
                                    await self._detect_intent_change()
                                    # If an agent change was triggered...  
                                    if self.target_agent_name is not None:   
                                        await self._reinitialize_session(realtime_client)
                                    
                                    # generate response once intent is detected and agent swap if necessary is completed
                                    await realtime_client.send(RealtimeEvent(service_type="response.create")) 

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
