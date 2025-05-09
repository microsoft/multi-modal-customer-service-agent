# Guideline on how to configure Azure Communication Service 

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- A deployed Communication Services resource. [Create a Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource).
- A [phone number](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/telephony/get-phone-number) in your Azure Communication Services resource that can get inbound calls. NB: phone numbers are not available in free subscriptions.
- [Python](https://www.python.org/downloads/) 3.9 or above.
- An Azure OpenAI Resource and Deployed Model. See [instructions](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource?pivots=web-portal).
- Install `uv`, see [the uv docs](https://docs.astral.sh/uv/getting-started/installation/).

### Setup and host your Azure DevTunnel

[Azure DevTunnels](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/overview) is an Azure service that enables you to share local web services hosted on the internet. Use the commands below to connect your local development environment to the public internet. This creates a tunnel with a persistent endpoint URL and which allows anonymous access. We will then use this endpoint to notify your application of calling events from the ACS Call Automation service.

```bash
devtunnel create --allow-anonymous
devtunnel port create -p 8080
devtunnel host
```


Copy the `.env.example` file to `.env` and update the following values:

1. `ACS_CONNECTION_STRING`: Azure Communication Service resource's connection string.
2. `CALLBACK_URI_HOST`: Base url of the app. (For local development use the dev tunnel url from the step above)
3. `REALTIME_URL`: Address of the realtime service
4. `PORT`: 8080

## Run the app

1. Start the rtmt.py service under `backend`: `python app.py` 
2. Start the acs application: `python acs_realtime.py`
3. Browser should pop up with a simple page. If not navigate it to `http://localhost:8080/` or your dev tunnel url.
4. Register an EventGrid Webhook for the IncomingCall(`https://<devtunnelurl>/api/incomingCall`) event that points to your devtunnel URI. Instructions [here](https://learn.microsoft.com/en-us/azure/communication-services/concepts/call-automation/incoming-call-notification).

Once that's completed you should have a running application. The way to test this is to place a call to your ACS phone number and talk to your intelligent agent!

In the terminal you should see all sorts of logs from both ACS and Semantic Kernel.
