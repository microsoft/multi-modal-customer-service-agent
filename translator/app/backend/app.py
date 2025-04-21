import os  
from dotenv import load_dotenv  
from aiohttp import web  
from azure.identity import DefaultAzureCredential  
from azure.core.credentials import AzureKeyCredential  
from rtmt import RTMiddleTier  
  
if __name__ == "__main__":  
    load_dotenv()  
    llm_endpoint = os.environ.get("AZURE_OPENAI_RT_ENDPOINT")  
    llm_deployment = os.environ.get("AZURE_OPENAI_RT_DEPLOYMENT")  
    llm_key = os.environ.get("AZURE_OPENAI_RT_API_KEY")  
  
    credentials = DefaultAzureCredential() if not llm_key else AzureKeyCredential(llm_key)  
  
    app = web.Application()  
    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, credentials)  
    # rtmt.attach_to_app(app, handshake_path="/handshake", realtime_path="/realtime")  

    # Attach your realtime endpoint only. (Remove serving the frontend static files)  
    rtmt.attach_to_app(app, "/realtime")  
    
    # Optional: define a basic route for health-checks  
    app.add_routes([  
        web.get('/', lambda request: web.json_response({"message": "Backend API is running."}))  
    ])  

    # Listen on 0.0.0.0 so that the container’s port is reachable externally.  
    web.run_app(app, host='0.0.0.0', port=8765)  
