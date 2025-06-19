# Observe application behavior

## Semantic Kernel and Observability

It's worth taking a minute to read these two pages about observability with semantic kernel:
[Observability in Semantic Kernel](https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/observability)

## Observability Architecture

This application uses the [Open Telemetry](https://opentelemetry.io/) standard for shipping application tracing data to three telemetry destinations:
- [.NET Aspire Dashboard](https://learn.microsoft.com/en-us/dotnet/aspire/fundamentals/dashboard/overview?tabs=bash), an OTEL-based dashboard for viewing application behavior.
- [Application Insights](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview), Azure's application observability service.
- Console log

## How does the app send telemetry data to observability destinations?

The application uses the python `opentelemetry` sdk to send data to various destinations. The sdk uses base classes `LogProvider`, `SpanProvider` and `MetricProvider` to send data to various endpoints. In [utility.py]('..\..\voice_agent\app\backend\utility.py) the application uses specific implementations of those classes to send telemetry data to the destinations.

## What observability resources are deployed to my resource group?

### Aspire Dashboard

The bicep infrastructure deploys Aspire Dashboard as a standalone ACA container called `aspire-dashboard`. You can find it in the list of resources in your resource group. Browse the dashboard by clicking the container link.

![Logical architecture](../../media/aspire_dashboard.png)

### Application Insights Resource

The bicep infrastructure deploys an Application Insights resource where you can observe your telemetry data. Use the following features to observe semantic kernel behavior in App Insights:

## Observe Application Behavior

### Local Configuration

You can see telemetry data if you are running the app locally, in a local dev container, or in Azure via `azd up`. If you are using GitHub Codespaces, there is no observability data. We recommend you run `azd up` and interact with the app in Azure environment to see observability data.

Configuration steps to wire up the Aspire Dashboard:
1. Update the `.env` file with this value: `TELEMETRY_SCENARIO=console,aspire_dashboard`
1. If running the app locally (no dev container), follow these steps:
    1. ```bash
        docker run --rm -it -d -p 18888:18888 -p 4317:18889 -e DOTNET_DASHBOARD_UNSECURED_ALLOW_ANONYMOUS=true --name aspire-dashboard mcr.microsoft.com/dotnet/aspire-dashboard:9.0
        ```
    2. In `.env`, set `ASPIRE_DASHBOARD_ENDPOINT` to `http://localhost:4317`
1. If running the app in a dev container, `docker-compose.yml` spins up the dashboard alongside your dev container. In `.env` set `ASPIRE_DASHBOARD_ENDPOINT` to `http://aspire-dashboard:18889` 
1. In the Azure environment, no additional steps are needed to configure observability.

### Conduct a conversation with the customer service agents

Conduct a conversation with the customer service agents following this sequence:
- Ask about your upcoming hotel stay
- Upgrade the room to a suite
- Ask about your upcoming flights
- Upgrade your seat to Business class

### Observe application behavior in Aspire Dashboard

Browse the Aspire Dashboard:
1. If running locally or in a dev container, go to [http://localhost:18888](http://localhost:18888)
1. If running in Azure:
- Go to your resource group in Azure Portal
- Click on the `aspire-dashboard` resource
- Click on the `Application URL` in the top right corner to navigate to the dashboard

See the observability data:
![Logs](../../media/aspire_dashboard_logs.png)
- Observe the application log showing the conversation you conducted. Locate an entry: "Function hotel_tools-load_user_reservation_info invoking." and click on the Trace link. This navigates you to the Trace page for that function call.
- Observe the details of the trace, such as the duration and other metadata.
![Trace Details](../../media/aspire_dashboard_trace_details.png)
- Click on the Traces navigation on the left.
- Observe the sequence of function calls and confirm it matches the conversation you had. Drill into traces to see information as desired.
![Traces](../../media/aspire_dashboard_traces.png)
- Click on the Metrics navigation on the left.
- Click on the function duration metric to see the duration on the most recent function calls.
![Metrics](../../media/aspire_dashboard_metrics.png)


## Application Environment Variables

- You can disable specific OTEL destinations by adjusting the `TELEMETRY_SCENARIO` variable. By default it is `console,application_insights,aspire_dashboard`. You can remove any destination from the list by and re-deploy by this sequence:
    - Go to the `backend` ACA app
    - Click on containers
    - Click on Environment Variables
    - Adjust the value as desired
    - Click `Deploy as new revision`. This will deploy a new revision of the backend app with your new value.
---
#### Navigation: [Home](../../README.md) | [Previous Section](../02_setup/README.md) | [Next Section](../04_explore/README.md)