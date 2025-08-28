import os, time, json
from azure.cosmos import CosmosClient, PartitionKey
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import AzureOpenAI
from typing import Any, Dict, List, Optional

load_dotenv()
# ==============
# Azure OpenAI Client Configuration (always Azure)
# ==============

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

# Cosmos DB configuration (always enabled)
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB = os.getenv("COSMOS_DB")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER")




# =========================
# Minimal trace
# =========================
@dataclass
class TraceEvent:
    s: str   # step
    st: str  # status
    p: Dict[str, Any]  # params
    ms: int  # elapsed ms

class TraceCollector:
    def __init__(self):
        self.events: List[TraceEvent] = []
        self._t0: Optional[float] = None

    def start(self):
        self._t0 = time.perf_counter()

    def record(self, step: str, status: str = "ok", **params):
        if self._t0 is None:
            self._t0 = time.perf_counter()
        elapsed = int((time.perf_counter() - self._t0) * 1000)
        self.events.append(TraceEvent(s=step, st=status, p=_compact(params), ms=elapsed))

    def to_list(self):
        # Ready to persist in JSON
        return [e.__dict__ for e in self.events]

def _compact(params: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        s = str(v)
        out[k] = (s[:200] + "…") if len(s) > 200 else s
    return out


# =========================
# Cosmos DB persistence
# =========================
def get_cosmos_client():
    return CosmosClient(COSMOS_URL, COSMOS_KEY)

def get_or_create_database(client):
    return client.create_database_if_not_exists(COSMOS_DB)

def get_or_create_container(db):
    return db.create_container_if_not_exists(
        id=COSMOS_CONTAINER,
        partition_key=PartitionKey(path="/conversationId"),
        offer_throughput=400,
    )

def save_to_cosmos(doc: Dict[str, Any]):
    client = get_cosmos_client()
    db = get_or_create_database(client)
    container = get_or_create_container(db)
    container.upsert_item(doc)


# =========================
# Transaction with streaming
# =========================
def run_chat_transaction_streaming(
    conversation_id: str,
    turn_id: str,
    user_input: str,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    trace = TraceCollector()
    trace.start()
    trace.record("preprocess", length=len(user_input), provider="azure-openai", model=client._azure_deployment)

    # Always use Azure OpenAI streaming with usage
    stream = client.chat.completions.create(
        model=client._azure_deployment,
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": user_input},
        ],
        stream=True,
        stream_options={"include_usage": True},
        temperature=temperature,
    )

    output_chunks: List[str] = []
    usage_final: Optional[Dict[str, Optional[int]]] = None

    # Process the stream
    for event in stream:
        # Incremental text
        if getattr(event, "choices", None):
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                output_chunks.append(delta.content)

        # The last chunk contains aggregated usage (total prompt/completion/total)
        if getattr(event, "usage", None):
            u = event.usage
            usage_final = {
                "prompt": getattr(u, "prompt_tokens", None),
                "completion": getattr(u, "completion_tokens", None),
                "total": getattr(u, "total_tokens", None),
            }

    output_text = "".join(output_chunks)
    trace.record("llm.chat.stream", length=len(output_text), have_usage=bool(usage_final))

    # Unified document (one row)
    doc = {
        "id": f"{conversation_id}:{turn_id}",
        "conversationId": conversation_id,
        "turnId": turn_id,
        "input": user_input,
        "output": output_text,
        "tokens": usage_final or {"prompt": None, "completion": None, "total": None},
        "trace": trace.to_list(),
        "ts": int(time.time()),
        "provider": "azure-openai",
        "model": client._azure_deployment,
    }

    # Always persist in CosmosDB
    save_to_cosmos(doc)
    return doc


# ==============
# Demo CLI
# ==============
if __name__ == "__main__":
    conv_id = "conv-001"
    turn_id = "001"
    question = "Give me 3 name ideas for a gym app with AI."

    result = run_chat_transaction_streaming(conv_id, turn_id, question)
    print("\n=== OUTPUT ===")
    print(result["output"])
    print("\n=== TOKENS ===")
    print(json.dumps(result["tokens"], indent=2, ensure_ascii=False))
    print("\n=== TRACE (compact) ===")
    print(json.dumps(result["trace"], indent=2, ensure_ascii=False))
    print("\nDocument saved in CosmosDB (partition key=conversationId).")
