"""
op1-SemanticTraceMini.py — Minimal Semantic Kernel + OpenTelemetry sample

Purpose
-------
Shortest clear example showing:
- Load env vars
- Configure Azure Monitor exporter
- Create one conversation + turn span
- Call Azure OpenAI via Semantic Kernel (single prompt, non‑streaming)
- Attach basic attributes + (best‑effort) token usage summary

Keep it small: no fallbacks, advanced metadata parsing, or extra abstractions.
If something required is missing, we fail fast with a concise message.

Required env vars:
  AZURE_OPENAI_API_KEY (or AZURE_OPENAI_KEY)
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_DEPLOYMENT
  APPINSIGHT_INSTRUMENTATION_KEY (or APPLICATIONINSIGHTS_CONNECTION_STRING)
Optional:
  AZURE_OPENAI_API_VERSION
  OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
  OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE=true

Run: python op1-SemanticTraceMini.py
"""

import asyncio
import os
import sys
from datetime import datetime, UTC

from dotenv import load_dotenv
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory, AuthorRole, ChatMessageContent

# ---------- Load config ----------
load_dotenv()
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
dep = os.getenv("AZURE_OPENAI_DEPLOYMENT")
key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv("APPINSIGHT_INSTRUMENTATION_KEY")
missing = [n for n, v in {
    "AZURE_OPENAI_ENDPOINT": endpoint,
    "AZURE_OPENAI_DEPLOYMENT": dep,
    "AZURE_OPENAI_API_KEY/AZURE_OPENAI_KEY": key,
    "APPINSIGHT_CONNECTION_STRING": conn,
}.items() if not v]
if missing:
    print(f"[ERROR] Missing: {', '.join(missing)}")
    sys.exit(1)

# Enable richer capture (optional defaults)
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE", "true")

# ---------- Telemetry exporter + instrument ----------
configure_azure_monitor(connection_string=conn, resource=Resource.create({
    "service.name": "CalabrioDemoKiko.SKMini",
    "service.version": "1.0.0",
}))
OpenAIInstrumentor().instrument()  # instrument underlying OpenAI client
tracer = trace.get_tracer(__name__)

# ---------- Semantic Kernel setup ----------
kernel = Kernel()
chat_service = AzureChatCompletion(api_key=key, endpoint=endpoint, deployment_name=dep, api_version=api_version)
kernel.add_service(chat_service)
settings = OpenAIChatPromptExecutionSettings(temperature=0.2, top_p=0.9, max_tokens=400)

async def run_once():
    prompt = "Tell me in 3 bullet points, why Semantic Kernel is cool"
    with tracer.start_as_current_span("conversation", attributes={
        "conversation.id": f"mini-{datetime.now(UTC).isoformat()}",
        "llm.deployment": dep,
        "llm.vendor": "azure-openai",
    }):
        with tracer.start_as_current_span("turn", attributes={"turn.role": "user", "turn.input.length": len(prompt)} ) as turn_span:
            history = ChatHistory()
            history.add_message(ChatMessageContent(role=AuthorRole.USER, content=prompt))
            messages = await chat_service.get_chat_message_contents(chat_history=history, settings=settings, kernel=kernel)
            answer = "".join([m.content or "" for m in messages])
            turn_span.set_attribute("turn.output.length", len(answer))
            turn_span.set_attribute("llm.temperature", settings.temperature or 0.0)
            turn_span.set_attribute("llm.top_p", settings.top_p or 0.0)
            # Token usage: rely entirely on OpenAI auto-instrumentation spans.
            # (Keeping manual capture out to keep file minimal.)
            print("\nUSER:\n", prompt, "\n\nASSISTANT:\n", answer)

if __name__ == "__main__":
    asyncio.run(run_once())
