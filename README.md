# Calabrio Chat Completion Telemetry Demo

## Overview
Current state: the repository now contains three active Python scripts demonstrating telemetry (and, for one script, Cosmos DB persistence). Legacy files referenced in earlier documentation (`tracingexample.py`, `PruebasAutoUsageTest.py`, `op1-NativeTracingTelemetry.py`, `op2-NativeTracingTelemetry.py`, `chainlit_app.py`) have been removed. This README only describes what is present today.

Conceptual approaches:
1. Option 1 (Native instrumentation): automatic SDK spans + token usage via `stream_options={"include_usage": True}` with minimal custom logic.
2. Option 2 (Cosmos persistence): chat example persisting turns (input/output + minimal trace info) into Cosmos DB; foundation to extend with token details, metrics, etc.

---
## File Map
| File | Purpose | Category |
|------|---------|----------|
| `op1-NativeTracingTelemetrySimpleCase.py` | Standalone single streaming request; adds manual token usage attributes and counters (prompt/completion/total). | Option 1 (standalone advanced) |
| `op1-NativeTracingTelemetryChat.py` | Minimal multi‑turn Chainlit chat: conversation/turn spans + automatic usage (no manual counters). | Option 1 (chat) |
| `op2-CosmosDBTracing.py` | Chainlit chat persisting turns in Cosmos DB (stores input/output + basic trace list). Extendable for tokens. | Option 2 (Cosmos) |
| `chainlit.md` | Chainlit welcome screen. | UI |
| `requirements.txt` | Dependencies (Chainlit, OpenAI, Cosmos, OpenTelemetry, etc.). | Infra |

Removed / legacy (not present): `tracingexample.py`, `PruebasAutoUsageTest.py`, `op1-NativeTracingTelemetry.py`, `op2-NativeTracingTelemetry.py`, `chainlit_app.py`.

---
## Environment Variables (.env)
There is a template file: `.fakeenv`. Copy it to `.env` and replace placeholder values:
```bash
cp .fakeenv .env
```
Never commit the real `.env`.

Azure OpenAI:
- `AZURE_OPENAI_API_KEY` (or `AZURE_OPENAI_KEY`)
- `AZURE_OPENAI_ENDPOINT` (https://<resource>.openai.azure.com/)
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION` (optional override; code sets a default if absent)

Telemetry / Azure Monitor:
- `APPINSIGHT_INSTRUMENTATION_KEY` (connection string)
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` (optional)
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE=true` (optional)

Cosmos DB (only for `op2-CosmosDBTracing.py`):
- `COSMOS_URL`
- `COSMOS_KEY`
- `COSMOS_DB`
- `COSMOS_CONTAINER`

---
## Running
### Dev Container (Recommended)
The repo includes a VS Code Dev Container (`.devcontainer/devcontainer.json`) based on image `mcr.microsoft.com/devcontainers/python:1-3.12-bullseye` with Azure CLI feature.

Prerequisites:
- Docker Desktop / compatible container runtime running.
- VS Code with the Dev Containers extension (or GitHub Codespaces).

Steps:
1. Clone repo.
2. Open folder in VS Code: it should prompt "Reopen in Container". Accept.
3. After build, the `postCreateCommand` installs Python deps from `requirements.txt`.
4. Create `.env` (copy from `.fakeenv`).
5. Run scripts/Chainlit commands as below.

### Local (Without Dev Container)
Prerequisites:
- Python 3.12 (match container image) recommended.
- `pip install -r requirements.txt` inside a virtualenv.
- (Optional) Azure CLI if you plan to interact with Azure resources manually.

Steps:
1. `python -m venv .venv && source .venv/bin/activate` (Linux/macOS) or `.venv\\Scripts\\activate` (Windows).
2. `pip install -r requirements.txt`.
3. `cp .fakeenv .env` and fill real values.
4. Run one of the execution modes below.

### 1. Standalone (tokens + counters)
```bash
python op1-NativeTracingTelemetrySimpleCase.py
```
Sample Kusto query (Application Insights) to view token attributes:
```kusto
traces
| where customDimensions["llm.usage.total_tokens"] != ''
| order by timestamp desc
```

### 2. Minimal chat (native instrumentation)
```bash
chainlit run op1-NativeTracingTelemetryChat.py
```

### 3. Chat with Cosmos DB persistence
Prepare the database/container and environment variables, then:
```bash
chainlit run op2-CosmosDBTracing.py
```

---
## Key Differences
| Aspect | Standalone SimpleCase | Chat Minimal | Chat Cosmos |
|--------|-----------------------|--------------|-------------|
| Streaming | Yes | Yes | Yes |
| SDK auto spans | Yes | Yes | Yes |
| Conversation span | No (single request span) | Yes | (Not implemented yet) |
| Turn span | No | Yes | No (can be added) |
| Custom token counters | Yes | No | No (template to extend) |
| Cosmos persistence | No | No | Yes |
| Manual token attributes | Yes | No (expects auto) | No (to extend) |

Note: `op2-CosmosDBTracing.py` currently persists input/output; the `tokens` dict is empty—populate it by reusing the standalone logic or extracting `event.usage` from the final streaming event.

---
## Adding Tokens to Cosmos (Quick Guide)
1. Capture the last `event.usage` object during streaming.
2. Before `upsert_item`, set `turn_doc["tokens"]` with `prompt_tokens`, `completion_tokens`, `total_tokens`.
3. (Optional) Add counters using `metrics.get_meter` as shown in the standalone script.

---
## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Missing spans | Missing `configure_azure_monitor` or connection string | Verify `APPINSIGHT_INSTRUMENTATION_KEY` |
| No token usage (chat) | Missing `stream_options.include_usage` or env flag | Add `stream_options={"include_usage": True}` + enable usage flag |
| Messages not grouped | No reusable conversation span | Create & store a root span in Chainlit session |
| Cosmos not persisting | Incomplete Cosmos env vars | Verify `COSMOS_*` values |

---
## Future Extensions
- Add root + per-turn spans to `op2-CosmosDBTracing.py` for full correlation.
- Populate token metrics & attributes in Cosmos turns.
- Latency histograms per deployment (OTel metrics).
- Quality / safety evaluation spans (groundedness, toxicity) appended to stored turns.

---
## Security Notes
- Do not commit real keys; keep them in `.env` (ignored by Git).
- Ensure compliance review before enabling message content capture (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`).
 - If using Codespaces / Dev Container, rotate any ephemeral keys after demos.

---
## Glossary
- Span: Trace unit (conversation, turn, model call).
- Usage: Token counts returned by Azure OpenAI.
- Instrumentation: Automatic span generation by SDK + OpenTelemetry.
- Turn: A user → assistant exchange.

---
End of current project state.
