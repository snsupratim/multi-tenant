"""
routers/auth.py – Registration, login, token refresh
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from backend.models.db_models import (
    User, UserCreate, UserLogin, TokenResponse, UserOut, UsageStat
)
from backend.utils.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate):
    # Check uniqueness
    if await User.find_one(User.email == payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await User.find_one(User.username == payload.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    # Namespace = user_id for Pinecone isolation
    await user.insert()
    user.pinecone_namespace = user.user_id
    await user.save()

    # Bootstrap usage stat document
    await UsageStat(user_id=user.user_id).insert()

    return UserOut(
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        plan=user.plan,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    user = await User.find_one(User.username == payload.username)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.username),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Not a refresh token")

    user = await User.find_one(User.user_id == payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.username),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.username,
        plan=current_user.plan,
        created_at=current_user.created_at,
    )
