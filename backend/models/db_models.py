"""
models/db_models.py – Beanie ODM document models for MongoDB
"""
from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import BaseModel, EmailStr, Field
import uuid


# ─── User ────────────────────────────────────────────────────────────────────

class User(Document):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    plan: str = "free"            # free | pro | enterprise
    pinecone_namespace: str = ""  # isolated namespace = user_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

    class Config:
        json_schema_extra = {
            "example": {
                "email": "alice@example.com",
                "username": "alice",
            }
        }


# ─── Document (uploaded file metadata) ───────────────────────────────────────

class DocumentRecord(Document):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    file_type: str          # pdf | docx | txt
    chunk_count: int = 0
    token_count: int = 0
    status: str = "processing"  # processing | ready | error
    error_msg: Optional[str] = None
    pinecone_namespace: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "documents"


# ─── Query Log ────────────────────────────────────────────────────────────────

class QueryLog(Document):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    query: str
    answer: str
    sources: List[str] = []
    latency_ms: int = 0
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "query_logs"


# ─── Usage Stats ──────────────────────────────────────────────────────────────

class UsageStat(Document):
    user_id: Indexed(str, unique=True)
    queries_today: int = 0
    uploads_today: int = 0
    total_queries: int = 0
    total_uploads: int = 0
    last_reset: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "usage_stats"

    async def reset_daily(self):
        if self.last_reset.date() < datetime.utcnow().date():
            self.queries_today = 0
            self.uploads_today = 0
            self.last_reset = datetime.utcnow()
            await self.save()


# ─── Pydantic Request / Response Schemas ─────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    user_id: str
    email: str
    username: str
    plan: str
    created_at: datetime


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    temperature: float = 0.3


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    latency_ms: int
    tokens_used: int


class DocumentOut(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    created_at: datetime


class StatsOut(BaseModel):
    queries_today: int
    uploads_today: int
    total_queries: int
    total_uploads: int
    document_count: int
