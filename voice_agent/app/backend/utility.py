import os, yaml, random, json, yaml, asyncio, time, aiohttp, urllib.request, ssl, redis, pickle, base64, logging
from typing import Any
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pathlib import Path
from scipy import spatial  # for calculating vector similarities for search
from typing import Dict

# Begin imports section for SK Logging, Tracing, and Metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

# Logs
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
)
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor


# Traces
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider

# Metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.metrics import set_meter_provider

# ------------------ Exporter Imports ------------------

# Console exporters
from opentelemetry.sdk._logs.export import ConsoleLogExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

# OTLP (for Aspire Dashboard/OTLP endpoints)
try:
    from opentelemetry.exporter.otlp.proto.grpc import OTLPLogExporter
except ImportError:
    OTLPLogExporter = None
try:
    from opentelemetry.exporter.otlp.proto.grpc import OTLPSpanExporter
except ImportError:
    OTLPSpanExporter = None
try:
    from opentelemetry.exporter.otlp.proto.grpc import OTLPMetricExporter
except ImportError:
    OTLPMetricExporter = None

# Azure Monitor (Application Insights) - installable via azure-monitor-opentelemetry-exporter
try:
    from azure.monitor.opentelemetry.exporter import (
        AzureMonitorLogExporter,
        AzureMonitorTraceExporter,
        AzureMonitorMetricExporter,
    )
except ImportError:
    AzureMonitorLogExporter = None
    AzureMonitorTraceExporter = None
    AzureMonitorMetricExporter = None

# Aggregation (optional, skip if not available)
try:
    from opentelemetry.sdk.metrics.aggregation import DropAggregation
    DROP_AGGREGATION_AVAILABLE = True
except ImportError:
    DROP_AGGREGATION_AVAILABLE = False

# Define logging scenarios and create logging, tracing, and metrics resources
DEFAULT_SERVICE_NAMES = {
    "console": "telemetry-console-quickstart",
    "application_insights": "telemetry-application-insights-quickstart",
    "aspire_dashboard": "telemetry-aspire-dashboard-quickstart",
}


def get_resource(scenario, service_name=None):
    """  
    Returns an OpenTelemetry Resource for the scenario, using the provided service_name if given, else a scenario-specific default.  
    """
    name = service_name or DEFAULT_SERVICE_NAMES.get(scenario, "telemetry-app")
    return Resource.create({ResourceAttributes.SERVICE_NAME: name})


def set_up_logging(scenario="console", connection_string=None, endpoint=None, service_name=None):
    """  
    Sets up OpenTelemetry logging.  
    :param scenario: "console", "application_insights", or "aspire_dashboard"  
    :param connection_string: Required for Application Insights  
    :param endpoint: Required for Aspire Dashboard/OTLP  
    :param service_name: Optional override for service name resource attribute  
    """
    resource = get_resource(scenario, service_name)

    if scenario == "console":
        exporter = ConsoleLogExporter()
    elif scenario == "application_insights":
        if AzureMonitorLogExporter is None:
            raise ImportError(
                "azure-monitor-opentelemetry-exporter is not installed. Please install it.")
        if not connection_string:
            raise ValueError(
                "connection_string is required for Application Insights logging")
        exporter = AzureMonitorLogExporter(connection_string=connection_string)
    elif scenario == "aspire_dashboard":
        if not endpoint:
            raise ValueError(
                "endpoint is required for Aspire Dashboard logging")
        exporter = OTLPLogExporter(endpoint=endpoint)
    else:
        raise ValueError(f"Invalid scenario: {scenario}")

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(logger_provider)

    # Attach OpenTelemetry to built-in logging (only for semantic_kernel logs, for SK compat)
    handler = LoggingHandler()
    handler.addFilter(logging.Filter("semantic_kernel"))
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def set_up_tracing(scenario="console", connection_string=None, endpoint=None, service_name=None):
    """  
    Sets up OpenTelemetry tracing.  
    :param scenario: "console", "application_insights", or "aspire_dashboard"  
    :param connection_string: Required for Application Insights  
    :param endpoint: Required for Aspire Dashboard/OTLP  
    :param service_name: Optional override for service name resource attribute  
    """
    resource = get_resource(scenario, service_name)

    if scenario == "console":
        exporter = ConsoleSpanExporter()
    elif scenario == "application_insights":
        if AzureMonitorTraceExporter is None:
            raise ImportError(
                "azure-monitor-opentelemetry-exporter is not installed. Please install it.")
        if not connection_string:
            raise ValueError(
                "connection_string is required for Application Insights tracing")
        exporter = AzureMonitorTraceExporter(
            connection_string=connection_string)
    elif scenario == "aspire_dashboard":
        if not endpoint:
            raise ValueError(
                "endpoint is required for Aspire Dashboard tracing")
        exporter = OTLPSpanExporter(endpoint=endpoint)
    else:
        raise ValueError(f"Invalid scenario: {scenario}")

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    set_tracer_provider(tracer_provider)


def set_up_metrics(scenario="console", connection_string=None, endpoint=None, service_name=None):
    """  
    Sets up OpenTelemetry metrics.  
    :param scenario: "console", "application_insights", or "aspire_dashboard"  
    :param connection_string: Required for Application Insights  
    :param endpoint: Required for Aspire Dashboard/OTLP  
    :param service_name: Optional override for service name resource attribute  
    """
    resource = get_resource(scenario, service_name)

    if scenario == "console":
        exporter = ConsoleMetricExporter()
    elif scenario == "application_insights":
        if AzureMonitorMetricExporter is None:
            raise ImportError(
                "azure-monitor-opentelemetry-exporter is not installed. Please install it.")
        if not connection_string:
            raise ValueError(
                "connection_string is required for Application Insights metrics")
        exporter = AzureMonitorMetricExporter(
            connection_string=connection_string)
    elif scenario == "aspire_dashboard":
        if not endpoint:
            raise ValueError(
                "endpoint is required for Aspire Dashboard metrics")
        exporter = OTLPMetricExporter(endpoint=endpoint)
    else:
        raise ValueError(f"Invalid scenario: {scenario}")

    views = [
        View(instrument_name="semantic_kernel*"),
    ]
    if DROP_AGGREGATION_AVAILABLE:
        views.insert(0, View(instrument_name="*", aggregation=DropAggregation()))
    meter_provider = MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                exporter, export_interval_millis=5000),
        ],
        resource=resource,
        views=views,
    )
    set_meter_provider(meter_provider)


# Configure basic logging (separate from those in OpenTelemetry for the logger named semantic_kernel above)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_entity(file_path, entity_name):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    for entity in data['agents']:
        if entity.get('name') == entity_name:
            return entity
    return None


# Load environment variables
load_dotenv()
async_client = AsyncAzureOpenAI(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
)
INTENT_SHIFT_API_KEY = os.environ.get("INTENT_SHIFT_API_KEY")
INTENT_SHIFT_API_URL = os.environ.get("INTENT_SHIFT_API_URL")
INTENT_SHIFT_API_DEPLOYMENT = os.environ.get("INTENT_SHIFT_API_DEPLOYMENT")
AZURE_OPENAI_4O_MINI_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_4O_MINI_DEPLOYMENT")


def allowSelfSignedHttps(allowed):
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context


allowSelfSignedHttps(True)


async def detect_intent(conversation):
    if INTENT_SHIFT_API_URL:
        start_time = time.time()
        # Prepare the request data
        # Format the data according to the ServiceInput schema
        value = f"{conversation}"
        data = {
            "input_data": {
                "columns": ["input_string"],
                "index": [0],
                # Wrap value in a list to match the expected structure
                "data": [[value]]
            },
            "params": {}
        }

        # Encode the data as JSON
        body = json.dumps(data).encode('utf-8')

        # Check if the API key is provided
        if not INTENT_SHIFT_API_KEY:
            raise Exception("A key should be provided to invoke the endpoint")

        # Set the headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {INTENT_SHIFT_API_KEY}',
            'azureml-model-deployment': INTENT_SHIFT_API_DEPLOYMENT
        }

        # Make the request
        req = urllib.request.Request(
            INTENT_SHIFT_API_URL, body, headers=headers)

        try:
            response = urllib.request.urlopen(req)
            result = response.read()
            result = json.loads(result)[0]['0'].strip()
            end_time = time.time()
            print(f"Job succeeded in {end_time - start_time:.2f} seconds.")
            return result

        except urllib.error.HTTPError as error:
            print("The request failed with status code: " + str(error.code))
            print(error.info())
            print(error.read().decode("utf8", 'ignore'))
            return None
    else:
        # fallback to gpt-4o-mini
        messages = [
            {"role": "system", "content": "You are a classifier model whose job is to classify the intent of the most recent user question into one of the following domains:\n\n- **hotel_agent**: Deal with hotel reservations, confirmations, changes, and general hotel policy questions.\n- **flight_agent**: Deal with flight reservations, confirmations, changes, and general airline policy questions.\n\nYou must only respond with the name of the predicted agent."},
            {"role": "user", "content": conversation}
        ]
        response = await async_client.chat.completions.create(
            model=AZURE_OPENAI_4O_MINI_DEPLOYMENT,
            messages=messages,
            max_tokens=20
        )
        intent = response.choices[0].message.content.strip()
        return intent


class SessionState:
    def __init__(self):
        # Redis configuration
        self.redis_client = None
        AZURE_REDIS_ENDPOINT = os.getenv("AZURE_REDIS_ENDPOINT")
        AZURE_REDIS_KEY = os.getenv("AZURE_REDIS_KEY")
        if AZURE_REDIS_KEY:  # use redis
            self.redis_client = redis.StrictRedis(
                host=AZURE_REDIS_ENDPOINT, port=6380, password=AZURE_REDIS_KEY, ssl=True)
            logger.info("Using Redis for session storage")
        else:  # use in-memory
            self.session_store: Dict[str, Dict] = {}

    def get(self, key):
        if self.redis_client:
            self.data = self.redis_client.get(key)
            return pickle.loads(base64.b64decode(self.data)) if self.data else None
        else:
            return self.session_store.get(key)

    def set(self, key, value):
        if self.redis_client:
            self.redis_client.set(key, base64.b64encode(pickle.dumps(value)))
        else:
            self.session_store[key] = value
