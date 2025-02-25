import os
from dotenv import load_dotenv
from aiohttp import web
# from ragtools import attach_rag_tools
from rtmt import RTMiddleTier
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

from aiohttp import web  
import base64  
from io import BytesIO  
from PIL import Image  

async def upload_video_frame(request):  
    try:  
        # Parse the incoming JSON data  
        data = await request.json()  
        frame_base64 = data.get("frame")  
        session_state_key = data.get("session_state_key")  # Extract session_state_key from the body  
  
        if not frame_base64:  
            return web.json_response({"error": "No frame data provided"}, status=400)  
  
        if not session_state_key:  
            return web.json_response({"error": "No session_state_key provided"}, status=400)  
        # Assuming image_data is obtained from base64.b64decode  

        # Store or process the frame using the session_state_key  
        rtmt.session_state.set(f"{session_state_key}_video", frame_base64)  
  
        return web.json_response({"status": "Frame received", "session_state_key": session_state_key})  
    except Exception as e:  
        return web.json_response({"error": str(e)}, status=500)    

  
# async def upload_video_frame(request):  
#     try:  
#         # Parse the incoming JSON data  
#         data = await request.json()  
#         frame_base64 = data.get("frame")  
#         session_state_key = data.get("session_state_key")  # Extract session_state_key from the body  
  
#         if not frame_base64:  
#             return web.json_response({"error": "No frame data provided"}, status=400)  
  
#         if not session_state_key:  
#             return web.json_response({"error": "No session_state_key provided"}, status=400)  
  
#         # Decode the base64 image  
#         image_data = base64.b64decode(frame_base64.split(",")[1])  
#         # image = Image.open(BytesIO(image_data))  
  
#         # Process the image or save it (for demo purposes, just log the session_state_key and size)  
#         # print(f"Received video frame for session_state_key: {session_state_key}, image size: {image.size}")  
  
#         # Store or process the frame using the session_state_key  
#         rtmt.session_state.set(f"{session_state_key}_video", image_data)  
  
#         return web.json_response({"status": "Frame received", "session_state_key": session_state_key})  
#     except Exception as e:  
#         return web.json_response({"error": str(e)}, status=500)    
if __name__ == "__main__":
    load_dotenv()
    llm_endpoint = os.environ.get("AZURE_OPENAI_RT_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_RT_DEPLOYMENT")
    llm_key = os.environ.get("AZURE_OPENAI_RT_API_KEY")
    search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    search_index = os.environ.get("AZURE_SEARCH_INDEX")
    search_key = os.environ.get("AZURE_SEARCH_API_KEY")

    credentials = DefaultAzureCredential() if not llm_key or not search_key else None

    app = web.Application()

    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, AzureKeyCredential(llm_key) if llm_key else credentials)

    rtmt.attach_to_app(app, "/realtime")

    app.add_routes([web.get('/', lambda _: web.FileResponse('./static/index.html'))])
    app.router.add_static('/', path='./static', name='static')
    app.router.add_post("/api/upload_video_frame", upload_video_frame)  

    web.run_app(app, host='localhost', port=8765)
