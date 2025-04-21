#!/usr/bin/env python  
  
"""ACS Realtime Integration Module (Per-Session Management)  
This module integrates Azure Communication Services (ACS) Call Automation with your  
realtime voice chat endpoint (exposed at /realtime). When a user calls, ACS  
notifies your endpoint via EventGrid. This module then:  
• Answers the call and sets up media streaming over WebSocket.  
• Appends the caller_id (e.g. phone number or identity string) as a query parameter  
  to the media streaming WebSocket URL.  
• In the /ws endpoint, the caller_id (extracted from the request’s query string) is  
  used as the session_state_key to open a connection to your realtime endpoint.  
• Bridges incoming audio from ACS to the realtime endpoint and sends realtime responses  
  back to ACS.  
  
Additional Setup / Guidelines:  
Environment Variables (set these in your .env file or your hosting environment):  
• ACS_CONNECTION_STRING : Your ACS resource connection string.  
• CALLBACK_URI_HOST : Public URL (or tunnel URL) of this module (e.g. via Azure DevTunnels).  
• REALTIME_URL : The WebSocket URL for your /realtime endpoint as a format string.  
  Example: ws://localhost:8765/realtime?session_state_key={session_id}  
• PORT : The port on which the Quart app will listen (default 8080).  
  
Dependencies:  
pip install quart aiohttp azure-communication-callautomation azure-eventgrid python-dotenv  
  
ACS Event Registration:  
Register the /api/incomingCall endpoint as the ACS IncomingCall webhook or via an EventGrid subscription.  
  
Make sure your realtime service (exposing /realtime) is running and accessible.  
  
To run this module:  
python acs_realtime_module.py  
"""  
  
import asyncio  
import base64  
import json  
import logging  
import os  
import uuid  
from urllib.parse import urlencode, urlparse, urlunparse  
  
import aiohttp  
import dotenv  
from quart import Quart, request, websocket, Response  
from azure.communication.callautomation.aio import CallAutomationClient  
from azure.communication.callautomation import (  
    AudioFormat,  
    MediaStreamingAudioChannelType,  
    MediaStreamingContentType,  
    MediaStreamingOptions,  
    MediaStreamingTransportType,  
)  
from azure.eventgrid import EventGridEvent, SystemEventNames  
  
# Load environment variables from .env file  
dotenv.load_dotenv()  
  
# Configure logging  
logging.basicConfig(level=logging.INFO)  
logger = logging.getLogger(__name__)  
  
# Initialize ACS Call Automation Client using the connection string  
ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING")  
if not ACS_CONNECTION_STRING:  
    raise ValueError("ACS_CONNECTION_STRING environment variable is not set.")  
acs_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)  
  
# Required environment variable for public callback URLs  
CALLBACK_URI_HOST = os.getenv("CALLBACK_URI_HOST")  
if not CALLBACK_URI_HOST:  
    raise ValueError("CALLBACK_URI_HOST environment variable is not set.")  
  
# REALTIME_URL is a format string with a {session_id} placeholder.  
# Example: "ws://localhost:8765/realtime?session_state_key={session_id}"  
REALTIME_URL = os.getenv("REALTIME_URL")  
if not REALTIME_URL:  
    raise ValueError("REALTIME_URL environment variable is not set.")  
  
# Initialize the Quart app  
app = Quart(__name__)  
  
  
@app.route("/")  
async def home():  
    return "ACS Realtime Integration Module Running"  
  
  
@app.route("/api/incomingCall", methods=["POST"])  
async def incoming_call_handler() -> Response:  
    """This endpoint is invoked by ACS (via EventGrid) when an incoming call is received.  
    It answers the call, extracts the caller_id, and sets up media streaming with a URL  
    that appends the caller_id as a query parameter.  
    """  
    logger.info("Received incoming call event")  
    events = await request.get_json()  
  
    for event_dict in events:  
        event = EventGridEvent.from_dict(event_dict)  
        logger.info("Processing event of type: %s", event.event_type)  
  
        # Handle EventGrid subscription validation events  
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:  
            logger.info("Validating subscription")  
            validation_code = event.data["validationCode"]  
            validation_response = {"validationResponse": validation_code}  
            return Response(  
                response=json.dumps(validation_response),  
                status=200,  
                mimetype="application/json",  
            )  
  
        if event.event_type == "Microsoft.Communication.IncomingCall":  
            logger.info("Incoming call event received: %s", event.data)  
  
            # Extract caller information – for a phone call, use the phone number.  
            caller_id = (  
                event.data["from"]["phoneNumber"]["value"]  
                if event.data["from"]["kind"] == "phoneNumber"  
                else event.data["from"]["rawId"]  
            )  
            logger.info("Caller ID (to be used as session_state_key): %s", caller_id)  
            incoming_call_context = event.data["incomingCallContext"]  
  
            # Create a unique ID for callback events.  
            guid = uuid.uuid4()  
  
            # Create query parameters with the callerId so that downstream endpoints can know the session.  
            query_parameters = urlencode({"callerId": caller_id})  
            callback_uri = f"{CALLBACK_URI_HOST}/api/callbacks/{guid}?{query_parameters}"  
  
            # Construct the media streaming WebSocket URL.  
            # Note: Append the same query_parameters so the /ws endpoint is aware of the caller.  
            parsed_url = urlparse(CALLBACK_URI_HOST)  
            ws_scheme = "wss" if parsed_url.scheme == "https" else "ws"  
            websocket_url = urlunparse(  
                (ws_scheme, parsed_url.netloc, "/ws", "", query_parameters, "")  
            )  
            logger.info("Callback URL: %s", callback_uri)  
            logger.info("Media streaming websocket URL: %s", websocket_url)  
  
            # Build media streaming options.  
            media_streaming_options = MediaStreamingOptions(  
                transport_url=websocket_url,  
                transport_type=MediaStreamingTransportType.WEBSOCKET,  
                content_type=MediaStreamingContentType.AUDIO,  
                audio_channel_type=MediaStreamingAudioChannelType.MIXED,  
                start_media_streaming=True,  
                enable_bidirectional=True,  
                audio_format=AudioFormat.PCM24_K_MONO,  
            )  
  
            # Answer the call.  
            answer_call_result = await acs_client.answer_call(  
                incoming_call_context=incoming_call_context,  
                operation_context="incomingCall",  
                callback_url=callback_uri,  
                media_streaming=media_streaming_options,  
            )  
            logger.info("Answered call. Connection ID: %s", answer_call_result.call_connection_id)  
  
    return Response(status=200)  
  
  
@app.route("/api/callbacks/<context_id>", methods=["POST"])  
async def callbacks(context_id):  
    """This endpoint processes callback events from ACS Call Automation.  
    Additional logic may be added here as needed.  
    """  
    events = await request.get_json()  
  
    for event in events:  
        event_data = event["data"]  
        logger.info(  
            "Received callback event: %s, CallConnectionId: %s",  
            event.get("type"),  
            event_data.get("callConnectionId"),  
        )  
  
    return Response(status=200)  
  
  
@app.websocket("/ws")  
async def acs_realtime_bridge():  
    """This WebSocket endpoint serves as the media streaming endpoint for ACS.  
    For each connection the endpoint retrieves the caller_id from the query parameters  
    and uses it as the session_state_key when connecting to the realtime endpoint.  
    Audio from ACS is forwarded to the realtime service, and responses are sent back.  
    """  
    # Extract caller_id from the WebSocket query parameters.  
    caller_id = websocket.args.get("callerId")
    if not caller_id:  
        error_msg = "No callerId provided in the query parameters."  
        logger.error(error_msg)  
        await websocket.send(json.dumps({"error": error_msg}))  
        return  
  
    # Construct the realtime endpoint URL by substituting the caller_id.  
    realtime_url = REALTIME_URL.format(session_id=caller_id)  
    logger.info("Connecting to realtime endpoint using URL: %s", realtime_url)  
  
    async with aiohttp.ClientSession() as session:  
        try:  
            async with session.ws_connect(realtime_url) as realtime_ws:  
                logger.info("Connected to /realtime endpoint.")  

                # Task: Forward audio messages from ACS (this WebSocket) to the realtime endpoint.  
                async def forward_acs_to_realtime():  
                    while True:  
                        try:  
                            message = await websocket.receive()  
                        except Exception as e:  
                            logger.error("Error receiving message from ACS websocket: %s", e)  
                            break  

                        try:  
                            data = json.loads(message)  
                        except Exception as e:  
                            logger.error("Error decoding ACS message: %s", e)  
                            continue  

                        # Check for valid audio message structure.  
                        if data.get("kind") == "AudioData" and "audioData" in data and "data" in data["audioData"]:  
                            audio_base64 = data["audioData"]["data"]  
                            realtime_message = {  
                                "type": "input_audio_buffer.append",  
                                "audio": audio_base64  
                            }  
                            try:  
                                await realtime_ws.send_json(realtime_message)  
                            except Exception as send_err:  
                                logger.error("Error sending message to realtime endpoint: %s", send_err)  
                                break  
                        else:  
                            logger.debug("Unhandled ACS message: %s", data)  

                # Task: Forward messages (audio responses) from the realtime endpoint back to ACS.  
                async def forward_realtime_to_acs():  
                    async for msg in realtime_ws:  
                        if msg.type == aiohttp.WSMsgType.TEXT:  
                            if msg.data is None:  
                                logger.error("Received empty message from realtime endpoint.")  
                                continue  
                            try:  
                                message = json.loads(msg.data)  
                            except Exception as e:  
                                logger.error("Error decoding realtime message: %s", e)  
                                continue  
                            if message and message.get("type") == "response.audio.delta" and "delta" in message:  
                                acs_message = {  
                                    "kind": "AudioData",  
                                    "audioData": {"data": message["delta"]}  
                                }  
                                try:  
                                    await websocket.send(json.dumps(acs_message))  
                                except Exception as send_err:  
                                    logger.error("Error sending realtime event to ACS: %s", send_err)  
                                    break  
                            elif message and message.get("type") == "input_audio_buffer.speech_started": #to interrupt the model's audio output

                                    await websocket.send(json.dumps({"Kind": "StopAudio", "AudioData": None, "StopAudio": {}}))

                            else:  
                                logger.debug("Unhandled realtime message: %s", message)  
                        elif msg.type == aiohttp.WSMsgType.ERROR:  
                            logger.error("Error in realtime websocket connection.")  
                            break  

                # Run both forwarding tasks concurrently.  
                await asyncio.gather(forward_acs_to_realtime(), forward_realtime_to_acs())  
        except Exception as e:  
            logger.error("Error connecting to /realtime endpoint: %s", e)  
            try:  
                await websocket.send(json.dumps({"error": str(e)}))  
            except Exception as se:  
                logger.error("Error sending error message to ACS websocket: %s", se)  

  
if __name__ == "__main__":  
    port = int(os.getenv("PORT", 8080))  
    app.run(port=port)  