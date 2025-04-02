import os
from dotenv import load_dotenv
from aiohttp import web
# from ragtools import attach_rag_tools
from rtmt import RTMiddleTier
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

load_dotenv()

if __name__ == "__main__":
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_RT_DEPLOYMENT")
    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")

    credentials = DefaultAzureCredential() if not llm_key else None

    app = web.Application()

    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, AzureKeyCredential(llm_key) if llm_key else credentials)

    # Attach your realtime endpoint only. (Remove serving the frontend static files)  
    rtmt.attach_to_app(app, "/realtime")  
    
    # Optional: define a basic route for health-checks  
    app.add_routes([  
        web.get('/', lambda request: web.json_response({"message": "Backend API is running."}))  
    ])  

    # Listen on 0.0.0.0 so that the container’s port is reachable externally.  
    web.run_app(app, host='0.0.0.0', port=8765)  
