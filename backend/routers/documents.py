"""
routers/documents.py – Document upload, list, delete
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks

from backend.models.db_models import User, DocumentRecord, DocumentOut, UsageStat
from backend.utils.auth import get_current_user
from backend.middleware.rate_limiter import rate_limiter
from backend.services.document_processor import ingest_document, delete_document

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_TYPES = {"pdf", "txt", "docx", "doc"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


async def _background_ingest(
    user_id: str, namespace: str, filename: str, content: bytes, doc_id: str
):
    """Run ingestion in background so upload endpoint returns immediately."""
    try:
        await ingest_document(user_id, namespace, filename, content, doc_id)
    except Exception as e:
        record = await DocumentRecord.find_one(DocumentRecord.doc_id == doc_id)
        if record:
            record.status = "error"
            record.error_msg = str(e)
            await record.save()


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # Rate limit check
    allowed = await rate_limiter.check_upload_limit(current_user.user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily upload limit of {50} files reached. Upgrade your plan.",
        )

    # File type check
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Read & size check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit.")

    # Create pending record
    doc_id = str(uuid.uuid4())
    record = DocumentRecord(
        doc_id=doc_id,
        user_id=current_user.user_id,
        filename=file.filename,
        file_type=ext,
        status="processing",
        pinecone_namespace=current_user.pinecone_namespace,
    )
    await record.insert()

    # Update usage
    stat = await UsageStat.find_one(UsageStat.user_id == current_user.user_id)
    if stat:
        await stat.reset_daily()
        stat.uploads_today += 1
        stat.total_uploads += 1
        await stat.save()

    # Kick off background ingestion
    background_tasks.add_task(
        _background_ingest,
        current_user.user_id,
        current_user.pinecone_namespace,
        file.filename,
        content,
        doc_id,
    )

    return DocumentOut(
        doc_id=record.doc_id,
        filename=record.filename,
        file_type=record.file_type,
        chunk_count=0,
        status="processing",
        created_at=record.created_at,
    )


@router.get("/", response_model=List[DocumentOut])
async def list_documents(current_user: User = Depends(get_current_user)):
    records = await DocumentRecord.find(
        DocumentRecord.user_id == current_user.user_id
    ).sort(-DocumentRecord.created_at).to_list()

    return [
        DocumentOut(
            doc_id=r.doc_id,
            filename=r.filename,
            file_type=r.file_type,
            chunk_count=r.chunk_count,
            status=r.status,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: str, current_user: User = Depends(get_current_user)):
    record = await DocumentRecord.find_one(
        DocumentRecord.doc_id == doc_id,
        DocumentRecord.user_id == current_user.user_id,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut(
        doc_id=record.doc_id,
        filename=record.filename,
        file_type=record.file_type,
        chunk_count=record.chunk_count,
        status=record.status,
        created_at=record.created_at,
    )


@router.delete("/{doc_id}", status_code=204)
async def remove_document(doc_id: str, current_user: User = Depends(get_current_user)):
    record = await DocumentRecord.find_one(
        DocumentRecord.doc_id == doc_id,
        DocumentRecord.user_id == current_user.user_id,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    success = await delete_document(doc_id, current_user.pinecone_namespace)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
