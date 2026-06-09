"""
services/embeddings.py – Google Gemini text-embedding-001 wrapper
"""
import asyncio
from typing import List
import google.generativeai as genai

from backend.config import settings

genai.configure(api_key=settings.google_api_key)

EMBEDDING_MODEL = settings.gemini_embedding_model   # "models/embedding-001"
EMBED_TASK_DOC  = "retrieval_document"
EMBED_TASK_QUERY = "retrieval_query"


async def embed_texts(texts: List[str], task_type: str = EMBED_TASK_DOC) -> List[List[float]]:
    """
    Embed a batch of texts using Gemini embedding-001.
    Returns a list of 768-dimensional float vectors.
    """
    loop = asyncio.get_event_loop()

    def _embed():
        results = []
        # Gemini API: batch up to 100 texts per call
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch,
                task_type=task_type,
            )
            # response["embedding"] is a list of vectors when content is a list
            embeddings = response["embedding"]
            if isinstance(embeddings[0], float):
                # Single text returned as flat list
                results.append(embeddings)
            else:
                results.extend(embeddings)
        return results

    return await loop.run_in_executor(None, _embed)


async def embed_query(query: str) -> List[float]:
    """Single query embedding optimised for retrieval."""
    vectors = await embed_texts([query], task_type=EMBED_TASK_QUERY)
    return vectors[0]


async def embed_documents(texts: List[str]) -> List[List[float]]:
    """Batch document embeddings."""
    return await embed_texts(texts, task_type=EMBED_TASK_DOC)
