# AI Assistant Project Instructions

These instructions orient AI coding agents working on this repository. Focus on accuracy, minimalism, and preserving existing telemetry patterns.

## Core Purpose
Demonstrate Azure OpenAI chat completions with OpenTelemetry instrumentation exported to Azure Monitor, plus an optional Cosmos DB persistence path. Three active scripts:
- `op1-NativeTracingTelemetrySimpleCase.py`: Single streamed request + manual token usage attributes + custom counters.
- `op1-NativeTracingTelemetryChat.py`: Minimal multi‑turn Chainlit chat using only automatic instrumentation (conversation + turn spans, automatic usage via `include_usage`).
- `op2-CosmosDBTracing.py`: Chainlit chat persisting each turn in Cosmos DB (tokens structure present but currently empty).
- You always write code in english, specially important for comments, descriptions and documentation.

## Telemetry Model
- OpenAI SDK instrumented via `OpenAIInstrumentor().instrument()`.
- Azure Monitor configured with `configure_azure_monitor(connection_string=...)` from `.env`.
- Option 1 chat: root `conversation` span + per `turn` span; manual token attributes only in standalone script.
- Token usage captured by streaming final event (`stream_options={"include_usage": True}`) + optional env flag `OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE=true`.

## Environment Variables
Defined in `.env` (never hard‑code):
- Azure OpenAI: `AZURE_OPENAI_API_KEY|AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`.
- Telemetry: `APPINSIGHT_INSTRUMENTATION_KEY`, optional `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`, `OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE`.
- Cosmos (only if using `op2-CosmosDBTracing.py`): `COSMOS_URL`, `COSMOS_KEY`, `COSMOS_DB`, `COSMOS_CONTAINER`.

## Conventions & Patterns
- Streaming loops append `delta.content` tokens and progressively update a single Chainlit message (avoid one-message-per-token spam).
- Store reusable spans (conversation span) in Chainlit session (`cl.user_session.set`).
- Attribute naming follows `llm.*` (e.g., `llm.usage.prompt_tokens`). Do not invent new prefixes without reason.
- Standalone script uses OpenTelemetry counters named `llm_prompt_tokens`, `llm_completion_tokens`, `llm_total_tokens`.
- Cosmos turn document structure (current minimal): `{ turnId, input, output, tokens: {}, trace: [...], ts, provider, model }`.

## When Extending
- Add conversation + turn spans to `op2-CosmosDBTracing.py` before introducing more metrics.
- Populate `tokens` dict using the last streaming event with `event.usage` (fields: `prompt_tokens`, `completion_tokens`, `total_tokens`).
- Keep metric & attribute naming consistent with existing usage to preserve dashboard continuity.
- If adding evaluation metrics, prefix clearly (e.g., `eval.groundedness.score`).

## Do / Avoid
- DO load config with `python-dotenv`; FAIL FAST if critical env vars missing in new scripts.
- DO reuse the existing Azure OpenAI client pattern (`AzureOpenAI(...)`).
- DO NOT commit secrets or sample `.env` with real values.
- DO NOT scatter multiple root spans per conversation; reuse stored one.
- DO NOT change dependency versions in `requirements.txt` without justification (telemetry compatibility risk).

## Typical Commands (for reference)
```bash
python op1-NativeTracingTelemetrySimpleCase.py
chainlit run op1-NativeTracingTelemetryChat.py
chainlit run op2-CosmosDBTracing.py
```

## Quality Checks Before PR
- Runs without uncaught exceptions.
- Token usage appears in traces (for scripts using usage capture).
- No hard-coded secrets or endpoints.
- New attributes use existing naming conventions.

## Small Extension Template (Tokens in Cosmos)
Pseudo steps:
```python
usage_data = None
for event in stream:
    # ... existing delta handling ...
    if getattr(event, 'usage', None):
        usage_data = event.usage
# before upsert
if usage_data:
    turn_doc['tokens'] = {
        'prompt_tokens': usage_data.prompt_tokens,
        'completion_tokens': usage_data.completion_tokens,
        'total_tokens': usage_data.total_tokens,
    }
```

## Contact Surface
If ambiguity arises, inspect README and mirror the existing style & naming. Prefer minimal, surgical edits.

(End of instructions)
