from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from models.user_model import User
from schemas import (
    LoginRequest,
    Token,
    UserCreate,
    UserResponse,
)
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    role = user_data.role.lower().strip()

    if role not in {"athlete", "coach"}:
        raise HTTPException(
            status_code=400,
            detail="Role must be athlete or coach",
        )

    existing_username = (
        db.query(User)
        .filter(
            User.username == user_data.username
        )
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already exists",
        )

    existing_email = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already exists",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        ),
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=Token,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(
            User.username == login_data.username
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
    }
@router.post("/token", response_model=Token)
def swagger_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == form_data.username)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
    }

# ============================================================
# CURRENT USER
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user


# ============================================================
# ATHLETE TEST AREA
# ============================================================

@router.get(
    "/athlete-area",
)
def athlete_area(
    current_user: User = Depends(
        require_role("athlete")
    ),
):
    return {
        "message": "Athlete access granted",
        "username": current_user.username,
        "role": current_user.role,
    }


# ============================================================
# COACH TEST AREA
# ============================================================

@router.get(
    "/coach-area",
)
def coach_area(
    current_user: User = Depends(
        require_role("coach")
    ),
):
    return {
        "message": "Coach access granted",
        "username": current_user.username,
        "role": current_user.role,
    }