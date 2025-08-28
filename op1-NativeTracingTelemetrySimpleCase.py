import os
from openai import AzureOpenAI
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry import trace, metrics
from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv

"""Simple standalone tracing & usage example.

This script demonstrates:
1. Loading all configuration from environment variables ('.env' file), avoiding hard-coded secrets.
2. Configuring Azure Monitor via OpenTelemetry for exporting traces & metrics.
3. Auto‑instrumenting the Azure OpenAI SDK (chat completions) to emit spans.
4. Performing ONE streamed chat completion while printing tokens as they arrive.
5. Capturing token usage (prompt/completion/total) from the final streaming event.
6. Attaching usage as span attributes + emitting custom counters for aggregation.

Environment variables required:
  AZURE_OPENAI_API_KEY (or legacy AZURE_OPENAI_KEY)
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_DEPLOYMENT
  AZURE_OPENAI_API_VERSION (optional, default 2024-12-01-preview)
  APPINSIGHT_INSTRUMENTATION_KEY (Azure Monitor connection string)
Optional for richer content capture:
  OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
  OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE=true
"""

# -------------------- Load environment --------------------
load_dotenv()

# Core Azure OpenAI config
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")

# Validate presence of critical variables early (fail fast for demos)
missing = [name for name, val in {
    "AZURE_OPENAI_ENDPOINT": endpoint,
    "AZURE_OPENAI_DEPLOYMENT": deployment,
    "AZURE_OPENAI_API_KEY/AZURE_OPENAI_KEY": subscription_key,
}.items() if not val]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

# Azure Monitor / Application Insights connection string
appinsight_connection_string = os.getenv("APPINSIGHT_INSTRUMENTATION_KEY")
if not appinsight_connection_string:
    raise RuntimeError("APPINSIGHT_INSTRUMENTATION_KEY not set in environment")

# -------------------- Configure Azure Monitor exporter --------------------
configure_azure_monitor(connection_string=appinsight_connection_string)

# -------------------- Instrument OpenAI SDK --------------------
OpenAIInstrumentor().instrument()

# -------------------- Prepare tracer & metrics --------------------
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
prompt_tokens_counter = meter.create_counter(
    "llm_prompt_tokens", description="Prompt tokens (single script)")
completion_tokens_counter = meter.create_counter(
    "llm_completion_tokens", description="Completion tokens (single script)")
total_tokens_counter = meter.create_counter(
    "llm_total_tokens", description="Total tokens (single script)")

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

with tracer.start_as_current_span(
    "single_chat_request",
    attributes={
        "llm.deployment": deployment,
        "llm.endpoint": endpoint,
        "demo.example": True,
    },
):
    # Build and send the streaming request (include_usage -> final chunk carries token usage)
    stream = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "I am going to Paris, what should I see?"},
        ],
        stream=True,
        stream_options={"include_usage": True},
        max_completion_tokens=800,
        temperature=1.0,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )
    usage_data = None  # Will hold token usage from the final event
    # Stream tokens to stdout as they arrive
    for event in stream:
        if getattr(event, "choices", None):
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                print(delta.content, end="")
        if hasattr(event, "usage") and event.usage:
            usage_data = event.usage
    # Attach usage to span + emit metrics
    if usage_data:
        def _extract(field):
            return getattr(usage_data, field, None) if hasattr(usage_data, field) else (usage_data.get(field) if isinstance(usage_data, dict) else None)
        prompt_tokens = _extract("prompt_tokens")
        completion_tokens = _extract("completion_tokens")
        total_tokens = _extract("total_tokens")
        span = trace.get_current_span()
        if prompt_tokens is not None:
            span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
            prompt_tokens_counter.add(prompt_tokens, {"deployment": deployment})
        if completion_tokens is not None:
            span.set_attribute("llm.usage.completion_tokens", completion_tokens)
            completion_tokens_counter.add(completion_tokens, {"deployment": deployment})
        if total_tokens is not None:
            span.set_attribute("llm.usage.total_tokens", total_tokens)
            total_tokens_counter.add(total_tokens, {"deployment": deployment})

print()  # Newline after streaming output
client.close()
