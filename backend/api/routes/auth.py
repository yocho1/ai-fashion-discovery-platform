from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import TokenRefresh, TokenResponse, UserLogin, UserRegister, UserResponse
from db.session import get_db_session
from services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db_session)) -> TokenResponse:
    """Register a new user and return JWT tokens."""
    try:
        user = AuthService.register_user(
            db, email=user_data.email, username=user_data.username, password=user_data.password, full_name=user_data.full_name
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    access_token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})
    refresh_token = AuthService.create_refresh_token(data={"sub": user.email, "user_id": user.id})

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_response)


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db_session)) -> TokenResponse:
    """Login user and return JWT tokens."""
    user = AuthService.authenticate_user(db, email=user_data.email, password=user_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})
    refresh_token = AuthService.create_refresh_token(data={"sub": user.email, "user_id": user.id})

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    token_data: TokenRefresh, db: Session = Depends(get_db_session)
) -> TokenResponse:
    """Refresh access token using refresh token."""
    payload = AuthService.verify_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_email = payload.get("sub")
    user = AuthService.get_user_by_email(db, email=user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})
    refresh_token = AuthService.create_refresh_token(data={"sub": user.email, "user_id": user.id})

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat(),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_response)
