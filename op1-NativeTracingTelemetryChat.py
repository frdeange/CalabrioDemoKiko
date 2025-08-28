import os
import chainlit as cl
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.trace import Span

"""op1-NativeTracingTelemetry.py (simplified)

Purpose: Minimal Chainlit + Azure OpenAI chat with conversation & turn spans
relying ONLY on include_usage=True + OpenAI instrumentation for token usage.

Removed: manual counters, manual span.set_attribute for usage.
Still present: root conversation span + per-turn span for correlation.
"""

# Load environment variables
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Read Application Insights connection string from .env
appinsight_connection_string = os.getenv("APPINSIGHT_INSTRUMENTATION_KEY")
configure_azure_monitor(connection_string=appinsight_connection_string)

# Instrument OpenAI SDK for tracing
OpenAIInstrumentor().instrument()

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)


@cl.on_chat_start
async def on_start():
    """Initialize conversation state (messages list) and create a root tracing span for the whole conversation."""
    tracer = trace.get_tracer(__name__)
    system_prompt = {"role": "system", "content": "You are a helpful assistant."}
    conversation_id = os.getenv("CHAINLIT_CONVERSATION_ID") or os.urandom(8).hex()
    # Root span kept open until chat end to correlate all LLM calls
    conversation_span: Span = tracer.start_span(
        name="conversation",
        attributes={
            "app.conversation.id": conversation_id,
            "llm.deployment": deployment,
            "llm.endpoint": endpoint,
        },
    )
    cl.user_session.set("conversation_id", conversation_id)
    cl.user_session.set("conversation_span", conversation_span)
    cl.user_session.set("messages", [system_prompt])
    await cl.Message(f"Conversación iniciada (id={conversation_id}). Pregúntame lo que quieras.").send()


@cl.on_message
async def main(message: cl.Message):
    """Handle each user message with streaming response and per-turn tracing span.

    Token usage expected to appear automatically in telemetry (if instrumentation +
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE are active) thanks to stream_options.
    """
    tracer = trace.get_tracer(__name__)
    conversation_span: Span | None = cl.user_session.get("conversation_span")
    conversation_id = cl.user_session.get("conversation_id")
    messages = cl.user_session.get("messages", [])
    user_msg = {"role": "user", "content": message.content}
    messages.append(user_msg)

    # Determine turn index (excluding system prompt)
    turn_index = sum(1 for m in messages if m["role"] == "user")

    # Prepare Chainlit message for streaming output
    streaming_msg = cl.Message(content="", author="assistant")
    await streaming_msg.send()

    # Build parent context so OpenAI instrumentation spans link under root conversation
    parent_ctx = trace.set_span_in_context(conversation_span) if conversation_span else None
    with tracer.start_as_current_span(
        name="turn",
        context=parent_ctx,
        attributes={
            "app.conversation.id": conversation_id,
            "app.turn.index": turn_index,
            "llm.deployment": deployment,
            "llm.temperature": 1.0,
        },
    ):
        try:
            stream = client.chat.completions.create(
                model=deployment,
                messages=messages,
                stream=True,
                temperature=1.0,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_completion_tokens=800,
                stream_options={"include_usage": True},
            )
            assistant_content = ""
            for event in stream:
                if getattr(event, "choices", None):
                    delta = event.choices[0].delta
                    if delta and getattr(delta, "content", None):
                        token = delta.content
                        assistant_content += token
                        streaming_msg.content += token
                        await streaming_msg.update()
            messages.append({"role": "assistant", "content": assistant_content})
            cl.user_session.set("messages", messages)
        except Exception as e:
            streaming_msg.content += f"\n[Error] {type(e).__name__}: {e}"
            await streaming_msg.update()


@cl.on_chat_end
async def on_end():
    """Close the shared AzureOpenAI client and end the root conversation span."""
    try:
        conversation_span: Span | None = cl.user_session.get("conversation_span")
        if conversation_span:
            conversation_span.end()
        client.close()
    except Exception:
        pass
