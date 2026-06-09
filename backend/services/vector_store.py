"""
services/vector_store.py – Pinecone client with per-user namespace isolation
"""
import asyncio
from typing import List, Dict, Any
from pinecone import Pinecone, ServerlessSpec

from backend.config import settings

# ─── Singleton Pinecone client ────────────────────────────────────────────────

_pc: Pinecone | None = None
_index = None


def _get_client() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=settings.pinecone_api_key)
    return _pc


def get_index():
    global _index
    if _index is None:
        pc = _get_client()
        existing = [i.name for i in pc.list_indexes()]
        if settings.pinecone_index_name not in existing:
            pc.create_index(
                name=settings.pinecone_index_name,
                dimension=3072,          # Gemini embedding-001 outputs 768-dim vectors
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.pinecone_environment,
                ),
            )
        _index = pc.Index(settings.pinecone_index_name)
    return _index


# ─── Vector operations ────────────────────────────────────────────────────────

class VectorStore:
    """
    All operations are scoped to a user's namespace = user_id.
    This guarantees complete tenant isolation inside a single Pinecone index.
    """

    def __init__(self, namespace: str):
        self.namespace = namespace
        self.index = get_index()

    async def upsert_chunks(
        self,
        vectors: List[Dict[str, Any]],
    ) -> int:
        """
        vectors: list of {"id": str, "values": List[float], "metadata": dict}
        Returns number of upserted vectors.
        """
        loop = asyncio.get_event_loop()

        def _upsert():
            batch_size = 100
            total = 0
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]
                self.index.upsert(vectors=batch, namespace=self.namespace)
                total += len(batch)
            return total

        return await loop.run_in_executor(None, _upsert)

    async def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filter: Dict | None = None,
    ) -> List[Dict[str, Any]]:
        """Returns list of matches with id, score, metadata."""
        loop = asyncio.get_event_loop()

        def _query():
            kwargs = dict(
                vector=vector,
                top_k=top_k,
                namespace=self.namespace,
                include_metadata=True,
            )
            if filter:
                kwargs["filter"] = filter
            return self.index.query(**kwargs)

        result = await loop.run_in_executor(None, _query)
        return [
            {
                "id": m.id,
                "score": m.score,
                "text": m.metadata.get("text", ""),
                "source": m.metadata.get("source", ""),
                "chunk_index": m.metadata.get("chunk_index", 0),
            }
            for m in result.matches
        ]

    async def delete_by_source(self, source: str) -> None:
        """Delete all vectors belonging to a specific document."""
        loop = asyncio.get_event_loop()

        def _delete():
            # Fetch IDs with matching source metadata, then delete
            results = self.index.query(
                vector=[0.0] * 768,
                top_k=10000,
                namespace=self.namespace,
                filter={"source": {"$eq": source}},
                include_metadata=False,
            )
            ids = [m.id for m in results.matches]
            if ids:
                self.index.delete(ids=ids, namespace=self.namespace)

        await loop.run_in_executor(None, _delete)

    async def delete_namespace(self) -> None:
        """Nuke the entire user namespace (account deletion)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.index.delete(delete_all=True, namespace=self.namespace),
        )

    async def namespace_stats(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, self.index.describe_index_stats)
        ns = stats.namespaces.get(self.namespace, {})
        return {
            "vector_count": getattr(ns, "vector_count", 0),
            "namespace": self.namespace,
        }
