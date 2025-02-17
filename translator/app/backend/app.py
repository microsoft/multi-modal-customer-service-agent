import os  
from dotenv import load_dotenv  
from aiohttp import web  
from azure.identity import DefaultAzureCredential  
from azure.core.credentials import AzureKeyCredential  
from rtmt_wip import RTMiddleTier  
  
if __name__ == "__main__":  
    load_dotenv()  
    llm_endpoint = os.environ.get("AZURE_OPENAI_RT_ENDPOINT")  
    llm_deployment = os.environ.get("AZURE_OPENAI_RT_DEPLOYMENT")  
    llm_key = os.environ.get("AZURE_OPENAI_RT_API_KEY")  
  
    credentials = DefaultAzureCredential() if not llm_key else AzureKeyCredential(llm_key)  
  
    app = web.Application()  
    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, credentials)  
    rtmt.attach_to_app(app, handshake_path="/handshake", realtime_path="/realtime")  
    # rtmt.attach_to_app(app,  path="/realtime")  

    app.add_routes([web.get('/', lambda _: web.FileResponse('./static/index.html'))])  
    app.router.add_static('/', path='./static', name='static')  
  
    web.run_app(app, host='localhost', port=8765)  