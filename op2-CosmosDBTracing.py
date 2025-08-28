
import chainlit as cl
import uuid
import time
from main import run_chat_transaction_streaming, get_cosmos_client, COSMOS_DB, COSMOS_CONTAINER
from azure.cosmos import PartitionKey

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
    from main import get_cosmos_client, COSMOS_DB, COSMOS_CONTAINER
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
    from main import get_cosmos_client, COSMOS_DB, COSMOS_CONTAINER, TraceCollector
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
    from main import client as openai_client
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
    for event in stream:
        if getattr(event, "choices", None):
            delta = event.choices[0].delta
            if delta and getattr(delta, "content", None):
                output_chunks.append(delta.content)
                msg.content += delta.content
                await msg.update()
    # Persist the turn in CosmosDB
    trace = TraceCollector()
    trace.start()
    trace.record("llm.chat.stream", length=len(msg.content), have_usage=True)
    turn_doc = {
        "turnId": turn_id,
        "input": message.content,
        "output": msg.content,
        "tokens": {},
        "trace": trace.to_list(),
        "ts": int(time.time()),
        "provider": "azure-openai",
        "model": openai_client._azure_deployment,
    }
    doc["turns"].append(turn_doc)
    container.upsert_item(doc)
