import os, time, uuid
import chainlit as cl
from azure.cosmos import CosmosClient, PartitionKey
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Cosmos DB configuration
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB = os.getenv("COSMOS_DB")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER")

# Cosmos helpers
def get_cosmos_client():
    return CosmosClient(COSMOS_URL, COSMOS_KEY)

# Minimal trace
class TraceEvent:
    def __init__(self, s: str, st: str, p: Dict[str, Any], ms: int):
        self.s = s
        self.st = st
        self.p = p
        self.ms = ms

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
        return [e.__dict__ for e in self.events]

def _compact(params: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        s = str(v)
        out[k] = (s[:200] + "…") if len(s) > 200 else s
    return out

# Helper to get next turn_id from CosmosDB for a conversation
def get_next_turn_id(conversation_id: str) -> str:
    client = get_cosmos_client()
    db = client.get_database_client(COSMOS_DB)
    container = db.get_container_client(COSMOS_CONTAINER)
    query = f"SELECT VALUE MAX(c.turnId) FROM c WHERE c.conversationId = '{conversation_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    max_turn = items[0] if items and items[0] is not None else 0
    return str(int(max_turn) + 1)

@cl.on_chat_start
async def start_chat():
    # Generate a new UUID for the conversation
    conversation_id = str(uuid.uuid4())
    cl.user_session.set("conversation_id", conversation_id)
    
    # Create initial document in CosmosDB with empty turns array
    client = get_cosmos_client()
    db = client.get_database_client(COSMOS_DB)
    container = db.get_container_client(COSMOS_CONTAINER)
    doc = {
        "id": conversation_id,
        "conversationId": conversation_id,
        "turns": []
    }
    container.upsert_item(doc)
    await cl.Message(f"New conversation started! Conversation ID: {conversation_id}").send()

@cl.on_message
async def handle_message(message):
    conversation_id = cl.user_session.get("conversation_id")
    
    # Get document from CosmosDB
    client = get_cosmos_client()
    db = client.get_database_client(COSMOS_DB)
    container = db.get_container_client(COSMOS_CONTAINER)
    doc = container.read_item(item=conversation_id, partition_key=conversation_id)
    turns = doc.get("turns", [])
    turn_id = str(len(turns) + 1)
    cl.user_session.set("turn_id", turn_id)

    # Prepare Chainlit message for streaming
    msg = cl.Message(content="", author="LLM")
    await msg.send()

    # Call LLM with streaming and update Chainlit message

    from openai import AzureOpenAI
    # Configurar cliente AzureOpenAI
    openai_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    )

    stream = openai_client.chat.completions.create(
        model=openai_client._azure_deployment,
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": message.content},
        ],
        stream=True,
        stream_options={"include_usage": True},
        temperature=0.2,
    )
    output_chunks = []
    usage_data = None
    for event in stream:
        if getattr(event, "choices", None):
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                output_chunks.append(delta.content)
                msg.content += delta.content
                await msg.update()
        if getattr(event, "usage", None):
            usage_data = event.usage

    # Persist the turn in CosmosDB
    trace = TraceCollector()
    trace.start()
    trace.record("llm.chat.stream", length=len(msg.content), have_usage=bool(usage_data))
    tokens = {}
    if usage_data:
        tokens = {
            "prompt_tokens": getattr(usage_data, "prompt_tokens", None),
            "completion_tokens": getattr(usage_data, "completion_tokens", None),
            "total_tokens": getattr(usage_data, "total_tokens", None),
        }
    turn_doc = {
        "turnId": turn_id,
        "input": message.content,
        "output": msg.content,
        "tokens": tokens,
        "trace": trace.to_list(),
        "ts": int(time.time()),
        "provider": "azure-openai",
        "model": openai_client._azure_deployment,
    }
    doc["turns"].append(turn_doc)
    container.upsert_item(doc)
