"""认证路由：注册 / 登录 / 刷新 Token"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.crud.user import get_user_by_username, get_user_by_email, create_user
from app.schemas.auth import TokenPair, LoginRequest, RegisterRequest, RefreshRequest
from app.schemas.user import UserPublic
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    if get_user_by_username(db, req.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = create_user(db, req)
    return user


@router.post("/login", response_model=TokenPair)
async def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 格式登录（用于 /docs 测试）"""
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    token_data = {"sub": str(user.id)}
    return TokenPair(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/login/json", response_model=TokenPair)
async def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    """JSON 格式登录（前端使用）"""
    user = get_user_by_username(db, req.username)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    token_data = {"sub": str(user.id)}
    return TokenPair(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """使用 Refresh Token 刷新 Access Token"""
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh Token 无效")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token 格式无效")

    user = get_user_by_username(db, user_id) or db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")

    token_data = {"sub": str(user.id)}
    return TokenPair(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UserPublic)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
