"""
routers/query.py – RAG query endpoint
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from backend.models.db_models import User, QueryRequest, QueryResponse, QueryLog, UsageStat
from backend.utils.auth import get_current_user
from backend.middleware.rate_limiter import rate_limiter
from backend.services.rag_pipeline import run_rag

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query_knowledge_base(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    # Per-user rate limit
    allowed = await rate_limiter.check_query_limit(current_user.user_id)
    if not allowed:
        remaining_reset = 60  # seconds
        raise HTTPException(
            status_code=429,
            detail=f"Query rate limit hit ({20}/min). Retry in ~{remaining_reset}s.",
        )

    answer, sources, latency_ms, tokens_used = await run_rag(
        user_id=current_user.user_id,
        namespace=current_user.pinecone_namespace,
        query=payload.query,
        top_k=payload.top_k,
        temperature=payload.temperature,
    )

    stat = await UsageStat.find_one(UsageStat.user_id == current_user.user_id)
    if stat:
        await stat.reset_daily()
        stat.queries_today += 1
        stat.total_queries += 1
        await stat.save()
    else:
        await UsageStat(
            user_id=current_user.user_id,
            queries_today=1,
            total_queries=1,
            last_reset=datetime.utcnow(),
        ).insert()

    await QueryLog(
        user_id=current_user.user_id,
        query=payload.query,
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
    ).insert()

    return QueryResponse(
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
    )


@router.get("/history")
async def query_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    logs = await QueryLog.find(
        QueryLog.user_id == current_user.user_id
    ).sort(-QueryLog.created_at).limit(limit).to_list()

    return [
        {
            "log_id": l.log_id,
            "query": l.query,
            "answer": l.answer,
            "sources": l.sources,
            "latency_ms": l.latency_ms,
            "tokens_used": l.tokens_used,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
