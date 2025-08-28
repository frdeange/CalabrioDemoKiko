# 🚀 Calabrio Chat Completion Telemetry Demo

<div align="center">

![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-326CE5?style=for-the-badge&logo=opentelemetry&logoColor=white)
![Cosmos DB](https://img.shields.io/badge/Cosmos%20DB-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)

*Complete telemetry demonstration for chat completions with Azure OpenAI*

</div>

## 📋 Overview

This repository contains **four active Python scripts** demonstrating different telemetry and persistence approaches for Azure OpenAI-based chat applications. All legacy files have been removed to keep the project clean and focused.

### 🎯 Conceptual Approaches

| 🔧 **Option 1: Native Instrumentation** | 🗃️ **Option 2: Cosmos Persistence** |
|:-----------------------------------------|:-------------------------------------|
| Automatic SDK spans + token usage | Chat examples persisting turns in Cosmos DB |
| `stream_options={"include_usage": True}` | Foundation to extend with token details and metrics |
| Minimal custom logic | Foundation for quality evaluations |

---

## 📁 File Map

<table>
<thead>
<tr>
<th>📄 File</th>
<th>🎯 Purpose</th>
<th>🏷️ Category</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>op1-NativeTracingTelemetrySimpleCase.py</code></td>
<td>📊 <strong>Standalone case</strong>: Single streaming request; adds manual token usage attributes and counters (prompt/completion/total)</td>
<td>🔧 Option 1 (standalone advanced)</td>
</tr>
<tr>
<td><code>op1-NativeTracingTelemetryChat.py</code></td>
<td>💬 <strong>Minimal multi-turn chat</strong>: conversation/turn spans + automatic usage (no manual counters)</td>
<td>🔧 Option 1 (chat)</td>
</tr>
<tr>
<td><code>op1-NativeTracingSemanticKernel.py</code></td>
<td>🧠 <strong>Minimal Semantic Kernel</strong>: single prompt (non-streaming); creates conversation + turn spans; automatic usage capture</td>
<td>🔧 Option 1 (Semantic Kernel)</td>
</tr>
<tr>
<td><code>op2-CosmosDBTracing.py</code></td>
<td>🗃️ <strong>Chat with persistence</strong>: persists turns in Cosmos DB (input/output + basic trace list). Extendable for tokens</td>
<td>🗃️ Option 2 (Cosmos)</td>
</tr>
<tr>
<td><code>chainlit.md</code></td>
<td>🏠 Chainlit welcome screen</td>
<td>🎨 UI</td>
</tr>
<tr>
<td><code>requirements.txt</code></td>
<td>📦 Dependencies (Chainlit, OpenAI, Cosmos, OpenTelemetry, etc.)</td>
<td>⚙️ Infrastructure</td>
</tr>
</tbody>
</table>

> ⚠️ **Removed/legacy files** (not present): `tracingexample.py`, `PruebasAutoUsageTest.py`, `op1-NativeTracingTelemetry.py`, `op2-NativeTracingTelemetry.py`, `chainlit_app.py`.

---

## 🔐 Environment Variables (.env)

> 📋 **Template available**: There is a `.fakeenv` file. Copy it to `.env` and replace placeholder values:

```bash
cp .fakeenv .env
```

> ⚠️ **IMPORTANT!** Never commit the real `.env` file.

### 🔵 Azure OpenAI
```env
AZURE_OPENAI_API_KEY=your_api_key_here          # or AZURE_OPENAI_KEY
AZURE_OPENAI_ENDPOINT=https://resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-01             # optional override
```

### 📊 Telemetry / Azure Monitor
```env
APPINSIGHT_INSTRUMENTATION_KEY=your_connection_string
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true  # optional
OTEL_INSTRUMENTATION_GENAI_CAPTURE_USAGE=true           # optional
```

### 🗃️ Cosmos DB (only for `op2-CosmosDBTracing.py`)
```env
COSMOS_URL=https://account.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key
COSMOS_DB=your_database_name
COSMOS_CONTAINER=your_container_name
```

---

## 🚀 How to Run

### 🐳 Dev Container (Recommended)

The repository includes a VS Code Dev Container (`.devcontainer/devcontainer.json`) based on image `mcr.microsoft.com/devcontainers/python:1-3.12-bullseye` with Azure CLI feature.

<details>
<summary><strong>📋 Prerequisites</strong></summary>

- ✅ Docker Desktop / compatible container runtime running
- ✅ VS Code with Dev Containers extension (or GitHub Codespaces)

</details>

#### 🔧 Setup Steps

1. **📥 Clone the repository**
2. **🖥️ Open folder in VS Code**: it should prompt "Reopen in Container". Accept.
3. **⏳ After build**: the `postCreateCommand` installs Python dependencies from `requirements.txt`
4. **🔐 Create `.env`** (copy from `.fakeenv`)
5. **▶️ Run** the scripts/Chainlit commands as shown below

### 💻 Local (Without Dev Container)

<details>
<summary><strong>📋 Prerequisites</strong></summary>

- ✅ Python 3.12 (to match container image) recommended
- ✅ `pip install -r requirements.txt` inside a virtualenv
- ✅ (Optional) Azure CLI if you plan to interact with Azure resources manually

</details>

#### 🔧 Setup Steps

```bash
# 1. Create and activate virtual environment
python -m venv .venv && source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .fakeenv .env
# Edit .env with real values

# 4. Run one of the execution modes below
```

---

## 🎮 Execution Modes

### 1️⃣ Standalone (tokens + counters)

```bash
python op1-NativeTracingTelemetrySimpleCase.py
```

<details>
<summary><strong>📊 Sample Kusto query (Application Insights)</strong></summary>

```kusto
traces
| where customDimensions["llm.usage.total_tokens"] != ''
| order by timestamp desc
```

</details>

### 2️⃣ Minimal chat (native instrumentation)

```bash
chainlit run op1-NativeTracingTelemetryChat.py
```

### 3️⃣ Chat with Cosmos DB persistence

> ⚠️ **Preparation**: Set up the database/container and environment variables first

```bash
chainlit run op2-CosmosDBTracing.py
```

### 4️⃣ Minimal Semantic Kernel (non-streaming)

```bash
python op1-NativeTracingSemanticKernel.py
```

> 🧠 **Description**: Single prompt answered via Semantic Kernel; emits one conversation + one turn span; relies on OpenAI auto-instrumentation for token usage (no manual counters, no streaming loop).

---

## 🔍 Key Differences

<table>
<thead>
<tr>
<th>🎯 Aspect</th>
<th>📊 Standalone SimpleCase</th>
<th>💬 Chat Minimal</th>
<th>🗃️ Chat Cosmos</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Streaming</strong></td>
<td>✅ Yes</td>
<td>✅ Yes</td>
<td>✅ Yes</td>
</tr>
<tr>
<td><strong>SDK auto spans</strong></td>
<td>✅ Yes</td>
<td>✅ Yes</td>
<td>✅ Yes</td>
</tr>
<tr>
<td><strong>Conversation span</strong></td>
<td>❌ No (single request span)</td>
<td>✅ Yes</td>
<td>⚠️ Not implemented yet</td>
</tr>
<tr>
<td><strong>Turn span</strong></td>
<td>❌ No</td>
<td>✅ Yes</td>
<td>❌ No (can be added)</td>
</tr>
<tr>
<td><strong>Custom token counters</strong></td>
<td>✅ Yes</td>
<td>❌ No (expects auto)</td>
<td>❌ No (template to extend)</td>
</tr>
<tr>
<td><strong>Cosmos persistence</strong></td>
<td>❌ No</td>
<td>❌ No</td>
<td>✅ Yes</td>
</tr>
<tr>
<td><strong>Manual token attributes</strong></td>
<td>✅ Yes</td>
<td>❌ No (expects auto)</td>
<td>❌ No (to extend)</td>
</tr>
</tbody>
</table>

> 📝 **Note**: `op2-CosmosDBTracing.py` currently persists input/output; the `tokens` dict is empty—populate it by reusing the standalone logic or extracting `event.usage` from the final streaming event.

---

## 🛠️ Adding Tokens to Cosmos (Quick Guide)

<details>
<summary><strong>📝 View implementation steps</strong></summary>

### Step 1: Capture the usage object
```python
usage_data = None
for event in stream:
    # ... existing delta handling ...
    if getattr(event, 'usage', None):
        usage_data = event.usage
```

### Step 2: Populate before upsert
```python
# before upsert_item
if usage_data:
    turn_doc['tokens'] = {
        'prompt_tokens': usage_data.prompt_tokens,
        'completion_tokens': usage_data.completion_tokens,
        'total_tokens': usage_data.total_tokens,
    }
```

### Step 3: (Optional) Add counters
```python
# Use metrics.get_meter as shown in the standalone script
```

</details>

---

## 🔧 Troubleshooting

<table>
<thead>
<tr>
<th>🚨 Symptom</th>
<th>🔍 Likely Cause</th>
<th>✅ Solution</th>
</tr>
</thead>
<tbody>
<tr>
<td>❌ Missing spans</td>
<td>Missing <code>configure_azure_monitor</code> or connection string</td>
<td>🔐 Verify <code>APPINSIGHT_INSTRUMENTATION_KEY</code></td>
</tr>
<tr>
<td>📊 No token usage (chat)</td>
<td>Missing <code>stream_options.include_usage</code> or env flag</td>
<td>⚙️ Add <code>stream_options={"include_usage": True}</code> + enable usage flag</td>
</tr>
<tr>
<td>📱 Messages not grouped</td>
<td>No reusable conversation span</td>
<td>🔄 Create & store a root span in Chainlit session</td>
</tr>
<tr>
<td>🗃️ Cosmos not persisting</td>
<td>Incomplete Cosmos env vars</td>
<td>✔️ Verify <code>COSMOS_*</code> values</td>
</tr>
</tbody>
</table>

---

## 🚀 Future Extensions

- 🔗 **Add root + per-turn spans** to `op2-CosmosDBTracing.py` for full correlation
- 📊 **Populate token metrics & attributes** in Cosmos turns
- ⏱️ **Latency histograms** per deployment (OTel metrics)
- 🎯 **Quality/safety evaluation spans** (groundedness, toxicity) appended to stored turns

---

## 🔒 Security Notes

<div align="center">

⚠️ **IMPORTANT: Keep your credentials secure** ⚠️

</div>

- 🚫 **Do not commit real keys**; keep them in `.env` (ignored by Git)
- 🛡️ **Ensure compliance review** before enabling message content capture (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`)
- 🔄 **If using Codespaces / Dev Container**, rotate any ephemeral keys after demos

---

## 📚 Glossary

| 🏷️ **Term** | 📝 **Definition** |
|:-------------|:------------------|
| **Span** | Trace unit (conversation, turn, model call) |
| **Usage** | Token counts returned by Azure OpenAI |
| **Instrumentation** | Automatic span generation by SDK + OpenTelemetry |
| **Turn** | A user → assistant exchange |

---

<div align="center">

### 🎉 End of current project state!

*Have questions? Check the documentation or open an issue!*

</div>
