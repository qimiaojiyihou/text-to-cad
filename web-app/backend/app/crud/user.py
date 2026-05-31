"""用户 CRUD 操作"""

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, db_user: User, user_in: UserUpdate) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    is_active: bool | None = None,
    is_superuser: bool | None = None,
) -> tuple[list[User], int]:
    """获取用户列表（支持搜索和筛选），返回 (用户列表, 总数)"""
    query = db.query(User)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_superuser is not None:
        query = query.filter(User.is_superuser == is_superuser)

    total = query.count()
    users = query.order_by(User.id.desc()).offset(skip).limit(limit).all()
    return users, total


def delete_user(db: Session, user_id: int) -> bool:
    """删除用户"""
    user = get_user(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def toggle_user_active(db: Session, user_id: int) -> User | None:
    """切换用户启用/禁用状态"""
    user = get_user(db, user_id)
    if not user:
        return None
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


def toggle_user_superuser(db: Session, user_id: int) -> User | None:
    """切换用户管理员权限"""
    user = get_user(db, user_id)
    if not user:
        return None
    user.is_superuser = not user.is_superuser
    db.commit()
    db.refresh(user)
    return user
