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
        data = await request.json()  
        frame_base64 = data.get("frame")  
        session_state_key = data.get("session_state_key")  
  
        if not frame_base64 or not session_state_key:  
            return web.json_response({"error": "Invalid data"}, status=400)  
  
        # Retrieve current frames list  
        frames = rtmt.session_state.get(f"{session_state_key}_video") or []  
        frames.append(frame_base64)  
        # Optionally limit the list to the last N frames  
        frames = frames[-1:]  # Keep only the last 1 frames  
  
        # Store the updated list back in the session state  
        rtmt.session_state.set(f"{session_state_key}_video", frames)  
  
        return web.json_response({"status": "Frame received"})  
    except Exception as e:  
        return web.json_response({"error": str(e)}, status=500)    
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
