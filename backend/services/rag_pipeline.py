"""
services/rag_pipeline.py – Retrieval-Augmented Generation with Groq LLaMA
"""
import time
from typing import List, Tuple

from groq import AsyncGroq

from backend.services.embeddings import embed_query
from backend.services.vector_store import VectorStore
from backend.models.db_models import QueryLog
from backend.config import settings

groq_client = AsyncGroq(api_key=settings.groq_api_key)

# ─── Prompt template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a precise, helpful AI assistant for a RAG-powered knowledge base.

RULES:
1. Answer ONLY using the provided context below.
2. If the context does not contain sufficient information, say: "I don't have enough information in the uploaded documents to answer this."
3. Always cite which document/source your answer comes from.
4. Be concise and structured. Use bullet points for lists.
5. Never fabricate information.
"""

def _build_user_prompt(query: str, context_chunks: List[dict]) -> str:
    context_text = "\n\n---\n\n".join(
        f"[Source: {c['source']}, Chunk {c['chunk_index']}]\n{c['text']}"
        for c in context_chunks
    )
    return f"""CONTEXT FROM KNOWLEDGE BASE:
{context_text}

---

USER QUESTION: {query}

Please answer based strictly on the context above."""


# ─── Main RAG function ────────────────────────────────────────────────────────

async def run_rag(
    user_id: str,
    namespace: str,
    query: str,
    top_k: int = 5,
    temperature: float = 0.3,
) -> Tuple[str, List[str], int, int]:
    """
    Returns: (answer, sources, latency_ms, tokens_used)
    """
    t0 = time.perf_counter()

    # 1. Embed query
    query_vector = await embed_query(query)

    # 2. Retrieve from Pinecone (user namespace)
    store = VectorStore(namespace=namespace)
    matches = await store.query(vector=query_vector, top_k=top_k)

    if not matches:
        answer = "No relevant documents found in your knowledge base. Please upload some documents first."
        sources = []
        latency_ms = int((time.perf_counter() - t0) * 1000)
        await _log_query(user_id, query, answer, sources, latency_ms, 0)
        return answer, sources, latency_ms, 0

    # 3. Build prompt
    user_prompt = _build_user_prompt(query, matches)

    # 4. Call Groq LLaMA
    completion = await groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=1024,
    )

    answer = completion.choices[0].message.content
    tokens_used = completion.usage.total_tokens if completion.usage else 0
    sources = list({m["source"] for m in matches})
    latency_ms = int((time.perf_counter() - t0) * 1000)

    # 5. Log to MongoDB
    await _log_query(user_id, query, answer, sources, latency_ms, tokens_used)

    return answer, sources, latency_ms, tokens_used


async def _log_query(
    user_id: str,
    query: str,
    answer: str,
    sources: List[str],
    latency_ms: int,
    tokens_used: int,
) -> None:
    log = QueryLog(
        user_id=user_id,
        query=query,
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
    )
    await log.insert()
