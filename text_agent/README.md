
#### 1. Environment preperation
- A virtual python environment (between 3.8 and 3.9)
- Install requirement.txt file

Please create a .env in this folder and provide details about the services.
```
AZURE_OPENAI_ENDPOINT=https://.openai.azure.com/
AZURE_OPENAI_API_KEY=YOUR_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EVALUATOR_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-04-01-preview
AZURE_OPENAI_EMB_DEPLOYMENT=text-embedding-ada-002
FLIGHT_POLICY_FILE=../data/flight_policy.json
HOTEL_POLICY_FILE=../data/hotel_policy.json
USER_PROFILE_FILE=../data/user_profile.json
HOTEL_DB_FILE=../data/hotel.db
FLIGHT_DB_FILE=../data/flight_db.db
AZURE_REDIS_KEY=#optional
AZURE_REDIS_ENDPOINT=#optional
API_HOST=localhost
API_PORT=8000
```
#### 2. Run the solution
```./run_services.sh```


