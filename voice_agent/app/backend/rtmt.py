#!/usr/bin/env python
"""  
Updated realtime voice AI agent using semantic_kernel for standardization.
This version demonstrates how to use an external/distributed session state
(via SessionState) and how to add a locking mechanism to avoid concurrent update issues.
Make sure to install semantic-kernel[realtime] along with your other dependencies.
"""

import os, asyncio, json, yaml, logging, base64
from enum import Enum
from typing import Any, Callable, Optional, Dict
from aiohttp import web
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from utility import detect_intent, SessionState, set_up_logging, set_up_tracing, set_up_metrics
from agents.tools.hotel_plugins import Hotel_Tools
from agents.tools.flight_plugins import Flight_Tools
from semantic_kernel.connectors.ai import FunctionChoiceBehavior


# Import Semantic Kernel classes
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureRealtimeExecutionSettings,
    AzureRealtimeWebsocket,
    TurnDetection,
    ListenEvents,
    SendEvents,
)
from semantic_kernel.contents import (
    AudioContent,
    ChatHistoryTruncationReducer,
    RealtimeTextEvent,
    RealtimeAudioEvent,
    RealtimeEvent,
    TextContent,
)

# Environment variables for easy configuration & deployment of telemetry
# Defaults to "console" if not set
# Options: "console", "application_insights", "aspire_dashboard"
# Can be set as a comma-separated list to enable multiple scenarios
TELEMETRY_SCENARIOS = os.getenv("TELEMETRY_SCENARIO", "console").split(",")
APP_INSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
ASPIRE_DASHBOARD_ENDPOINT = os.getenv("ASPIRE_DASHBOARD_ENDPOINT")
# Optional, overrides scenario default
CUSTOM_SERVICE_NAME = os.getenv("SERVICE_NAME")


# --- Multi-endpoint OpenTelemetry setup ---
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import set_tracer_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.metrics.view import View
from opentelemetry.metrics import set_meter_provider
try:
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
except ImportError:
    OTLPLogExporter = OTLPSpanExporter = OTLPMetricExporter = None
try:
    from azure.monitor.opentelemetry.exporter import (
        AzureMonitorLogExporter, AzureMonitorTraceExporter, AzureMonitorMetricExporter
    )
except ImportError:
    AzureMonitorLogExporter = AzureMonitorTraceExporter = AzureMonitorMetricExporter = None
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

log_exporters = []
span_exporters = []
metric_readers = []
views = [View(instrument_name="semantic_kernel*")]

def get_resource(service_name):
    return Resource.create({ResourceAttributes.SERVICE_NAME: service_name or "telemetry-app"})

for scenario in TELEMETRY_SCENARIOS:
    scenario = scenario.strip()
    service_name = CUSTOM_SERVICE_NAME
    if scenario == "console":
        log_exporters.append(ConsoleLogExporter())
        span_exporters.append(ConsoleSpanExporter())
        metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=5000))
    elif scenario == "application_insights":
        if AzureMonitorLogExporter and AzureMonitorTraceExporter and AzureMonitorMetricExporter:
            if not APP_INSIGHTS_CONNECTION_STRING:
                raise ValueError("APPLICATIONINSIGHTS_CONNECTION_STRING is required for Application Insights telemetry")
            log_exporters.append(AzureMonitorLogExporter(connection_string=APP_INSIGHTS_CONNECTION_STRING))
            span_exporters.append(AzureMonitorTraceExporter(connection_string=APP_INSIGHTS_CONNECTION_STRING))
            metric_readers.append(PeriodicExportingMetricReader(AzureMonitorMetricExporter(connection_string=APP_INSIGHTS_CONNECTION_STRING), export_interval_millis=5000))
        else:
            raise ImportError("azure-monitor-opentelemetry-exporter is not installed. Please install it.")
    elif scenario == "aspire_dashboard":
        print('OTLPLogExporter:', OTLPLogExporter)
        print('OTLPSpanExporter:', OTLPSpanExporter)
        print('OTLPMetricExporter:', OTLPMetricExporter)
        if OTLPLogExporter and OTLPSpanExporter and OTLPMetricExporter:
            if not ASPIRE_DASHBOARD_ENDPOINT:
                raise ValueError("ASPIRE_DASHBOARD_ENDPOINT is required for Aspire Dashboard telemetry")
            log_exporters.append(OTLPLogExporter(endpoint=ASPIRE_DASHBOARD_ENDPOINT))
            span_exporters.append(OTLPSpanExporter(endpoint=ASPIRE_DASHBOARD_ENDPOINT))
            metric_readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=ASPIRE_DASHBOARD_ENDPOINT), export_interval_millis=5000))
        else:
            raise ImportError("opentelemetry-exporter-otlp-proto-grpc is not installed. Please install it.")
    else:
        raise ValueError(f"Invalid telemetry scenario: {scenario}")

# Set up logging provider
logger_provider = LoggerProvider(resource=get_resource(CUSTOM_SERVICE_NAME))
for exporter in log_exporters:
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
set_logger_provider(logger_provider)
# Attach OpenTelemetry to built-in logging (only for semantic_kernel logs, for SK compat)
handler = LoggingHandler()
handler.addFilter(logging.Filter("semantic_kernel"))
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

# Set up tracing provider
tracer_provider = TracerProvider(resource=get_resource(CUSTOM_SERVICE_NAME))
for exporter in span_exporters:
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
set_tracer_provider(tracer_provider)

# Set up metrics provider
meter_provider = MeterProvider(resource=get_resource(CUSTOM_SERVICE_NAME), views=views, metric_readers=metric_readers)
set_meter_provider(meter_provider)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --------------------------- RTMiddleTier Class ---------------------------
class RTMiddleTier:
    model: Optional[str] = None
    agents: list[dict] = []
    agent_names: list[str] = []
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    disable_audio: Optional[bool] = False
    max_history_length = 3
    _token_provider = None
    use_classification_model: bool = True

    # Distributed session state object. This uses Redis if available, otherwise in-memory.
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

        # Load agent profiles and associated tools. Note that we leave the agent “persona”
        # as a template (with placeholders) so that customer details can be injected per session.
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

        # A dictionary to hold all session-specific state.
        # Keys: session_state_key; Values: dict holding current_agent, current_agent_kernel, history, etc.
        self.sessions: dict[str, dict] = {}

    def _load_agents(self):
        base_path = "agents/agent_profiles"
        agent_profiles = [f for f in os.listdir(
            base_path) if f.endswith("_profile.yaml")]
        for profile in agent_profiles:
            profile_path = os.path.join(base_path, profile)
            with open(profile_path, "r") as file:
                try:
                    data = yaml.safe_load(file)
                    # Leave persona as a template – do not format with customer info here.
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
        self.default_agent = next(
            agent for agent in self.agents if agent.get("default_agent"))
        self.default_agent_kernel = self.kernels.get(
            self.default_agent.get("name"))

    def _format_instructions(self, agent: dict, session: dict) -> str:
        # Helper method to format the agent's persona template with session-specific customer details.
        template = agent.get("persona", "")
        return template.format(
            customer_name=session.get("customer_name", "John Doe"),
            customer_id=session.get("customer_id", "12345")
        )

    # ----------------- Session-specific helper methods -----------------
    async def _detect_intent_change(self, session: dict):
        # Use the session’s own conversation history and current agent.
        extracted_history = [
            f"{item.role.value}: {item.items[0].text}" for item in session["history"]
        ]
        logger.info("Current agent: %s", session["current_agent"].get("name"))
        conversation = "\n".join(extracted_history)
        intent = await detect_intent(conversation)
        logger.info("Detected intent: %s", intent)
        if intent in self.agent_names and intent != session["current_agent"].get("name"):
            session["target_agent_name"] = intent
            logger.info("Switching to new agent: %s",
                        session["target_agent_name"])
            session["transfer_conversation"] = True

    async def _reinitialize_session(self, realtime_client: AzureRealtimeWebsocket, session: dict):
        await realtime_client.send(RealtimeEvent(service_type="input_audio_buffer.clear"))
        # Update instructions dynamically when switching agents:
        session["current_agent"] = next(
            (agent for agent in self.agents if agent.get(
                "name") == session["target_agent_name"]), None
        )
        session["current_agent_kernel"] = self.kernels.get(
            session["current_agent"].get("name"))
        # Format the new agent's persona with session-specific customer details.
        formatted_instructions = self._format_instructions(
            session["current_agent"], session)
        if session.get("realtime_settings"):
            session["realtime_settings"].instructions = formatted_instructions
        await realtime_client.update_session(
            settings=session["realtime_settings"],
            kernel=session["current_agent_kernel"]
        )
        session["transfer_conversation"] = False
        session["target_agent_name"] = None

    # -------------- Main realtime message forwarding (per session) --------------
    async def _forward_messages(self, session_state_key: str, session: dict, ws: web.WebSocketResponse):
        logger.info("Starting Semantic Kernel based realtime session")

        # Build the realtime session settings using the session’s current agent
        # and a formatted version of its persona (with the customer name and id).
        formatted_instructions = self._format_instructions(
            session["current_agent"], session)
        session["realtime_settings"] = AzureRealtimeExecutionSettings(
            instructions=formatted_instructions,
            turn_detection=TurnDetection(
                type=os.environ.get("TURN_DETECTION_MODEL", "server_vad"),
                threshold=float(os.environ.get(
                    "TURN_DETECTION_THRESHOLD", 0.5)),
                prefix_padding_ms=int(os.environ.get(
                    "TURN_DETECTION_PREFIX_PADDING_MS", 300)),
                silence_duration_ms=int(os.environ.get(
                    "TURN_DETECTION_SILENCE_DURATION_MS", 200)),
                create_response=False
            ),
            input_audio_transcription={"model": os.environ.get(
                "TRANSCRIPTION_MODEL", "whisper-1")},
            input_audio_format="pcm16",
            output_audio_format="pcm16",
            voice=os.environ.get("VOICE_NAME", "ash"),
            temperature=self.temperature,
            max_response_output_tokens=self.max_tokens,
            disable_audio=self.disable_audio,
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
        )

        realtime_client = AzureRealtimeWebsocket()

        async with realtime_client(
            settings=session["realtime_settings"],
            kernel=session["current_agent_kernel"],
            chat_history=session["history"]
        ):

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
                        if msg_type == SendEvents.SESSION_UPDATE:
                            pass
                        # Forward appended audio from the client.
                        elif msg_type == SendEvents.INPUT_AUDIO_BUFFER_APPEND:
                            audio_data = message.get("audio")
                            if audio_data:
                                await realtime_client.send(
                                    event=RealtimeAudioEvent(
                                        audio=AudioContent(
                                            data=audio_data, data_format="base64"),
                                    )
                                )

                        # Forward clear-buffer commands.
                        elif msg_type == SendEvents.INPUT_AUDIO_BUFFER_CLEAR:
                            clear_event = RealtimeEvent(
                                service_type=SendEvents.INPUT_AUDIO_BUFFER_CLEAR.value,
                            )
                            await realtime_client.send(clear_event)
                        else:
                            logger.warning(
                                "Unhandled client message type: %s", msg_type)
                    else:
                        logger.error(
                            "Unexpected message type from client: %s", msg.type)

            async def from_realtime_to_client():
                async for event in realtime_client.receive():
                    match event:
                        case RealtimeAudioEvent():
                            audio_data = event.audio.data
                            audio_base64 = base64.b64encode(
                                audio_data).decode('ascii')
                            await ws.send_json({
                                "type": "response.audio.delta",
                                "delta": audio_base64
                            })
                        case _:
                            match event.service_type:
                                case ListenEvents.RESPONSE_AUDIO_TRANSCRIPT_DONE:
                                    logger.info(
                                        "Received response transcription.completed event: %s", event.service_event.transcript)
                                    transcript = event.service_event.transcript
                                    session["history"].add_assistant_message(
                                        transcript)

                                    # Retain only the last n turns.
                                    await session["history"].reduce()
                                    self.session_state.set(
                                        session_state_key, session["history"])

                                case ListenEvents.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
                                    logger.info(
                                        "Received input transcription.completed event: %s", event.service_event.transcript)
                                    transcript = event.service_event.transcript
                                    if len(transcript) > 0:
                                        session["history"].add_user_message(
                                            transcript)

                                        # Trigger intent detection – if enabled – so that conversation can be transferred.
                                        if self.use_classification_model:
                                            await self._detect_intent_change(session)
                                            if session.get("target_agent_name") is not None:
                                                await self._reinitialize_session(realtime_client, session)

                                            # Generate response once intent is detected or agent swap (if any) is complete.
                                            if session["active_response"] == False:
                                                await realtime_client.send(RealtimeEvent(service_type="response.create"))

                                    await session["history"].reduce()
                                    self.session_state.set(
                                        session_state_key, session["history"])

                                case ListenEvents.RESPONSE_CREATED:
                                    session["active_response"] = True

                                case ListenEvents.RESPONSE_DONE:
                                    session["active_response"] = False
                                    if event.service_event.response.status != "completed":
                                        logger.info(
                                            "response.done event status: %s", event.service_event.response.status)
                                        logger.info("response.done event status reason: %s",
                                                    event.service_event.response.status_details.reason)

                                case _:
                                    try:
                                        # For other events, convert any pydantic models to a dictionary.
                                        e_payload = event.service_event
                                        if hasattr(e_payload, "dict"):
                                            e_payload = e_payload.dict()
                                        await ws.send_json(e_payload)
                                    except Exception as e:
                                        logger.error(
                                            "Error sending realtime event to client: %s", e)

            await asyncio.gather(from_client_to_realtime(), from_realtime_to_client())

    async def _websocket_handler(self, session_state_key: str, session: dict, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self._forward_messages(session_state_key, session, ws)
        return ws

    def attach_to_app(self, app, path):
        async def _handler_with_session_key(request: web.Request):
            # Get session_state_key and customer information from query parameters.
            session_state_key = request.query.get(
                "session_state_key", "default_session_id")
            logger.info("Session state key: %s", session_state_key)

            # Extract session-specific customer details from query parameters.
            customer_name = request.query.get("customer_name", "John Doe")
            customer_id = request.query.get("customer_id", "12345")

            # Try retrieving any backup conversation from persistent session_state.
            init_history = self.session_state.get(session_state_key)
            logger.info("Initial history: %s", init_history)
            # Check if we already have a session for this key.
            session = self.sessions.get(session_state_key)
            if session is None:
                if init_history is None:
                    init_history = ChatHistoryTruncationReducer(
                        target_count=self.max_history_length)
                session = {
                    "current_agent": self.default_agent,
                    "current_agent_kernel": self.default_agent_kernel,
                    "history": init_history,
                    "target_agent_name": None,
                    "transfer_conversation": False,
                    "active_response": False,
                    "realtime_settings": None,
                    "customer_name": customer_name,
                    "customer_id": customer_id,
                }
                self.sessions[session_state_key] = session
            else:
                if init_history:
                    session["history"] = init_history
                session["customer_name"] = customer_name
                session["customer_id"] = customer_id
            return await self._websocket_handler(session_state_key, session, request)

        app.router.add_get(path, _handler_with_session_key)
