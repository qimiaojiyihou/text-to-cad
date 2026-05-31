"""JWT 鉴权与密码工具"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

from jose import JWTError, jwt
import bcrypt

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def _prehash_password(password: str) -> bytes:
    """预哈希密码以处理超过72字节的问题"""
    return hashlib.sha256(password.encode("utf-8")).digest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    prehashed = _prehash_password(plain_password)
    return bcrypt.checkpw(prehashed, hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    prehashed = _prehash_password(password)
    salt = bcrypt.gensalt(rounds=settings.PASSWORD_HASH_ROUNDS)
    hashed = bcrypt.hashpw(prehashed, salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Access Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """创建 JWT Refresh Token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
