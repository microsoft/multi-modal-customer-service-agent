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
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 256
    disable_audio: Optional[bool] = False
    max_history_length = 3
    _token_provider = None
    use_classification_model: bool = True

    # A global session state backup 
    session_state = SessionState()  

    # Global Semantic Kernel objects keyed by agent name (shared among sessions)  
    kernels: dict[str, Kernel] = {}  

    # Global realtime connectivity parameters (the same for every session)  
    deployment: str  
    endpoint: str  
    key: Optional[str] = None  

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | DefaultAzureCredential):  
        # Initialize the Semantic Kernel (global to the process)  
        self.kernel = Kernel()  

        # Load agent profiles and associated tools  
        self._load_agents()  
        self.endpoint = endpoint  
        self.deployment = deployment  
        if isinstance(credentials, AzureKeyCredential):  
            self.key = credentials.key  
        else:  
            self._token_provider = get_bearer_token_provider(  
                credentials, "https://cognitiveservices.azure.com/.default"  
            )  
            self._token_provider()  # Warm up token  

        # A dictionary to hold all session-specific state  
        # Keys: session_state_key; Values: dict holding current_agent, current_agent_kernel, history, etc.  
        self.sessions: dict[str, dict] = {}  

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
                    # Update persona using values from the user profile.  
                    data["persona"] = data["persona"].format(  
                        customer_name=user_profile["name"],  
                        customer_id=user_profile["customer_id"]  
                    )  
                    self.agents.append(data)  
                    agent_name = data.get("name")  
                    self.kernels[agent_name] = Kernel()  
                    if agent_name == "hotel_agent":  
                        self.kernels[agent_name].add_plugin(  
                            plugin=Hotel_Tools(),  
                            plugin_name="hotel_tools",  
                            description="tools for hotel agent"  
                        )  
                    elif agent_name == "flight_agent":  
                        self.kernels[agent_name].add_plugin(  
                            plugin=Flight_Tools(),  
                            plugin_name="flight_tools",  
                            description="tools for flight agent"  
                        )  
                except yaml.YAMLError as exc:  
                    logger.error("Error loading %s: %s", profile, exc)  
        self.agent_names = [agent["name"] for agent in self.agents]  
        logger.info("Available agents: %s", self.agent_names)  
        # Save the default agent and its kernel for new sessions.  
        self.default_agent = next(agent for agent in self.agents if agent.get("default_agent"))  
        self.default_agent_kernel = self.kernels.get(self.default_agent.get("name"))  

    # ----------------- Session-specific helper methods -----------------  
    async def _detect_intent_change(self, session: dict):  
        # Use the session’s own conversation history and current agent.  
        extracted_history = [  
            f"{item['item']['role']}: {item['item']['content'][0]['text']}" for item in session["history"]  
        ]  
        logger.info("Current agent: %s", session["current_agent"].get("name"))  
        conversation = "\n".join(extracted_history)  
        intent = await detect_intent(conversation)  
        logger.info("Detected intent: %s", intent)  
        if intent in self.agent_names and intent != session["current_agent"].get("name"):  
            session["target_agent_name"] = intent  
            logger.info("Switching to new agent: %s", session["target_agent_name"])  
            session["transfer_conversation"] = True  

    async def _reinitialize_session(self, realtime_client: AzureRealtimeWebsocket, session: dict):  
        await realtime_client.send(RealtimeEvent(service_type="input_audio_buffer.clear"))  
        # Update instructions dynamically when switching agents:  
        session["current_agent"] = next(  
            (agent for agent in self.agents if agent.get("name") == session["target_agent_name"]), None  
        )  
        session["current_agent_kernel"] = self.kernels.get(session["current_agent"].get("name"))  
        # Update realtime_settings instructions with the new agent's persona.  
        if session.get("realtime_settings"):  
            session["realtime_settings"].instructions = session["current_agent"].get("persona")  
        await realtime_client.update_session(  
            settings=session["realtime_settings"],  
            kernel=session["current_agent_kernel"]  
        )  
        session["transfer_conversation"] = False  
        session["target_agent_name"] = None  

    # -------------- Main realtime message forwarding (per session) --------------  
    async def _forward_messages(self, session_state_key: str, session: dict, ws: web.WebSocketResponse):  
        logger.info("Starting Semantic Kernel based realtime session")  

        # Build the realtime session settings using the session’s current agent.  
        session["realtime_settings"] = AzureRealtimeExecutionSettings(  
            instructions=session["current_agent"].get("persona"),  
            turn_detection=TurnDetection(  
                type=os.environ.get("TURN_DETECTION_MODEL", "server_vad"),  
                threshold=os.environ.get("TURN_DETECTION_THRESHOLD", 0.5),  
                prefix_padding_ms=os.environ.get("TURN_DETECTION_PREFIX_PADDING_MS", 300), 
                silence_duration_ms=os.environ.get("TURN_DETECTION_SILENCE_DURATION_MS", 200), 
                create_response=False  
            ),  
            input_audio_transcription={"model": os.environ.get("TRANSCRIPTION_MODEL", "whisper-1")},  
            input_audio_format="pcm16",  
            output_audio_format="pcm16",  
            voice=os.environ.get("VOICE_NAME","ash"),  
            temperature=self.temperature,  
            max_response_output_tokens=self.max_tokens,  
            disable_audio=self.disable_audio,  
            function_choice_behavior=FunctionChoiceBehavior.Auto(),  
        )  

        realtime_client = AzureRealtimeWebsocket()  

        async with realtime_client(settings=session["realtime_settings"], kernel=session["current_agent_kernel"]):  

            async def from_client_to_realtime():  
                async for msg in ws:  
                    if msg.type == web.WSMsgType.TEXT:  
                        try:  
                            message = json.loads(msg.data)  
                        except Exception as e:  
                            logger.error("Error parsing client message: %s", e)  
                            continue  
                        msg_type = message.get("type")  
                        # Client session.update commands (unused in this example)  
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
                        elif isinstance(event.service_event, ResponseAudioTranscriptDoneEvent):  
                            logger.info("Received response transcription.completed event: %s", event.service_event.transcript)  
                            transcript = event.service_event.transcript  
                            session["history"].append({  
                                "type": "conversation.item.create",  
                                "item": {  
                                    "type": "message",  
                                    "status": "completed",  
                                    "role": "assistant",  
                                    "content": [{  
                                        "type": "text",  
                                        "text": transcript  
                                    }]  
                                }  
                            })  
                            # Retain only the last n turns.  
                            session["history"] = session["history"][-self.max_history_length:]  
                            self.session_state.set(session_state_key, session["history"])  

                        elif isinstance(event.service_event, ConversationItemInputAudioTranscriptionCompletedEvent):  
                            logger.info("Received input transcription.completed event: %s", event.service_event.transcript)  
                            transcript = event.service_event.transcript  
                            if len(transcript) > 0:  
                                session["history"].append({  
                                    "type": "conversation.item.create",  
                                    "item": {  
                                        "type": "message",  
                                        "status": "completed",  
                                        "role": "user",  
                                        "content": [{  
                                            "type": "input_text",  
                                            "text": transcript  
                                        }]  
                                    }  
                                })  
                                # Trigger intent detection – if enabled – so that conversation can be transferred.  
                                if self.use_classification_model:  
                                    await self._detect_intent_change(session)  
                                    if session.get("target_agent_name") is not None:  
                                        await self._reinitialize_session(realtime_client, session)  
                                    # Generate response once intent is detected or agent swap (if any) is complete.  
                                    await realtime_client.send(RealtimeEvent(service_type="response.create"))  
                            if len(session["history"]) > self.max_history_length:  
                                session["history"].pop(0)  
                            self.session_state.set(session_state_key, session["history"])  
                        else:  
                            # For other events, convert any pydantic models to a dictionary.  
                            e_payload = event.service_event  
                            if hasattr(e_payload, "dict"):  
                                e_payload = e_payload.dict()  
                            await ws.send_json(e_payload)  
                    except Exception as e:  
                        logger.error("Error sending realtime event to client: %s", e)  

            await asyncio.gather(from_client_to_realtime(), from_realtime_to_client())  

    async def _websocket_handler(self, session_state_key: str, session: dict, request: web.Request) -> web.WebSocketResponse:  
        ws = web.WebSocketResponse()  
        await ws.prepare(request)  
        await self._forward_messages(session_state_key, session, ws)  
        return ws  

    def attach_to_app(self, app, path):  
        async def _handler_with_session_key(request: web.Request):  
            # Get session_state_key from query parameters (defaulting if needed)  
            session_state_key = request.query.get("session_state_key", "default_session_id")  
            logger.info("Session state key: %s", session_state_key)  

            # Try retrieving any backup conversation from persistent session_state.  
            init_history = self.session_state.get(session_state_key)  
            # Check if we already have a session for this key.  
            session = self.sessions.get(session_state_key)  
            if session is None:  
                # Create a new session with the defaults loaded from _load_agents.  
                if init_history is None:  
                    init_history = []  
                session = {  
                    "current_agent": self.default_agent,  
                    "current_agent_kernel": self.default_agent_kernel,  
                    "history": init_history,  
                    "target_agent_name": None,  
                    "transfer_conversation": False,  
                    "realtime_settings": None,  
                }  
                self.sessions[session_state_key] = session  
            else:  
                # If the session already exists, you could also refresh its history from backup if desired.  
                if init_history:  
                    session["history"] = init_history  
            return await self._websocket_handler(session_state_key, session, request)  

        app.router.add_get(path, _handler_with_session_key)  