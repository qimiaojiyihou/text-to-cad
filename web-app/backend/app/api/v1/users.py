"""用户管理路由（管理员后台）"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_user, get_current_superuser
from app.crud.user import (
    get_user, update_user, get_users, delete_user,
    toggle_user_active, toggle_user_superuser
)
from app.schemas.user import UserPublic, UserUpdate, UserAdminUpdate, UserListResponse
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户信息"""
    return update_user(db, current_user, req)


# ---------------------------------------------------------------------------
# Admin only
# ---------------------------------------------------------------------------

@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="搜索用户名/邮箱/昵称"),
    is_active: bool | None = Query(None, description="筛选启用状态"),
    is_superuser: bool | None = Query(None, description="筛选管理员"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """管理员：获取用户列表（支持分页、搜索、筛选）"""
    users, total = get_users(
        db, skip=skip, limit=limit,
        search=search, is_active=is_active, is_superuser=is_superuser
    )
    return UserListResponse(
        items=[UserPublic.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserPublic)
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """管理员：查看指定用户信息"""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.patch("/{user_id}", response_model=UserPublic)
async def admin_update_user(
    user_id: int,
    req: UserAdminUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """管理员：更新用户信息（包括权限和状态）"""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return update_user(db, user, req)


@router.delete("/{user_id}")
async def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_superuser),
):
    """管理员：删除用户（不能删除自己）"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True, "message": "用户已删除"}


@router.post("/{user_id}/toggle-active", response_model=UserPublic)
async def admin_toggle_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_superuser),
):
    """管理员：切换用户启用/禁用状态"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能禁用当前登录的管理员账号")
    user = toggle_user_active(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/{user_id}/toggle-superuser", response_model=UserPublic)
async def admin_toggle_superuser(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_superuser),
):
    """管理员：切换用户管理员权限"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能修改当前登录管理员自己的权限")
    user = toggle_user_superuser(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
