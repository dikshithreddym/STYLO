from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_async_db, User
from app.schemas import UserCreate, UserResponse, Token, UserUpdate
from app.utils.auth import get_password_hash, verify_password, create_access_token, get_current_user_async
from app.config import settings

# Rate limiter for auth endpoints (uses same key function as main app)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Not authenticated - invalid or missing credentials"},
        429: {"description": "Too many requests - rate limit exceeded"},
    }
)


@router.post("/signup", response_model=UserResponse)
@limiter.limit("5/minute")  # Prevent signup abuse
async def create_user(request: Request, user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password, full_name=user.full_name, gender=user.gender)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Prevent brute force attacks
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    # OAuth2PasswordRequestForm stores email in 'username' field
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user_async)):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_users_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async)
):
    # Update only provided fields
    updated = False
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
        updated = True
    if payload.gender is not None:
        current_user.gender = payload.gender
        updated = True

    if not updated:
        return current_user

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
