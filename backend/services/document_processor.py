"""
services/document_processor.py – Parse, chunk, embed, and upsert documents
"""
import io
import uuid
import asyncio
from typing import List, Tuple
from datetime import datetime

import PyPDF2
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.services.embeddings import embed_documents
from backend.services.vector_store import VectorStore
from backend.models.db_models import DocumentRecord
from backend.config import settings

# ─── Text splitter config ─────────────────────────────────────────────────────

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ─── Parsers ──────────────────────────────────────────────────────────────────

def _parse_pdf(content: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _parse_docx(content: bytes) -> str:
    doc = docx.Document(io.BytesIO(content))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _parse_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def parse_file(filename: str, content: bytes) -> Tuple[str, str]:
    """Returns (raw_text, file_type)."""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return _parse_pdf(content), "pdf"
    elif ext in ("docx", "doc"):
        return _parse_docx(content), "docx"
    elif ext == "txt":
        return _parse_txt(content), "txt"
    else:
        raise ValueError(f"Unsupported file type: .{ext}")


# ─── Main ingestion pipeline ──────────────────────────────────────────────────

async def ingest_document(
    user_id: str,
    namespace: str,
    filename: str,
    content: bytes,
    doc_id: str,
) -> DocumentRecord:
    """
    Full ingestion pipeline:
      1. Parse → raw text
      2. Chunk → list of text chunks
      3. Embed → Gemini vectors
      4. Upsert → Pinecone (namespace isolated)
      5. Update → MongoDB DocumentRecord
    """
    # 1. Parse
    raw_text, file_type = parse_file(filename, content)

    # 2. Chunk
    chunks: List[str] = SPLITTER.split_text(raw_text)
    if not chunks:
        raise ValueError("Document produced no usable text chunks.")

    # 3. Embed
    vectors_list = await embed_documents(chunks)

    # 4. Build Pinecone vectors
    pinecone_vectors = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors_list)):
        pinecone_vectors.append({
            "id": f"{doc_id}__chunk__{i}",
            "values": vector,
            "metadata": {
                "text": chunk,
                "source": filename,
                "doc_id": doc_id,
                "chunk_index": i,
                "user_id": user_id,
            },
        })

    # 5. Upsert
    store = VectorStore(namespace=namespace)
    await store.upsert_chunks(pinecone_vectors)

    # 6. Persist metadata to MongoDB
    record = await DocumentRecord.find_one(DocumentRecord.doc_id == doc_id)
    if record:
        record.chunk_count = len(chunks)
        record.token_count = sum(len(c.split()) for c in chunks)
        record.status = "ready"
        record.file_type = file_type
        await record.save()
    else:
        record = DocumentRecord(
            doc_id=doc_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            chunk_count=len(chunks),
            token_count=sum(len(c.split()) for c in chunks),
            status="ready",
            pinecone_namespace=namespace,
        )
        await record.insert()

    return record


async def delete_document(doc_id: str, namespace: str) -> bool:
    """Remove from Pinecone + MongoDB."""
    record = await DocumentRecord.find_one(DocumentRecord.doc_id == doc_id)
    if not record:
        return False

    store = VectorStore(namespace=namespace)
    await store.delete_by_source(record.filename)
    await record.delete()
    return True
