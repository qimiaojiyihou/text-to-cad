# Text-to-CAD Web App 架构设计

## 一、模块划分

```
web-app/
├── frontend/          # 前台：用户登录 + CAD 生成 + 历史记录
├── admin/             # 后台：用户管理 + 权限管理 + 生成记录查看
├── backend/           # API 服务：为 frontend + admin 提供统一后端
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py        # 登录/注册/刷新
│   │   │   ├── cad.py         # CAD 生成/任务/模型下载
│   │   │   ├── admin_users.py # 用户管理（仅 admin）
│   │   │   ├── admin_roles.py # 权限/角色管理（仅 admin）
│   │   │   └── admin_records.py # 生成记录查看（仅 admin）
│   │   ├── core/              # 配置、安全、权限
│   │   ├── models/            # SQLAlchemy ORM 模型
│   │   ├── schemas/           # Pydantic 校验模型
│   │   ├── crud/              # 数据库操作封装
│   │   └── db/                # 数据库连接、初始化
│   └── main.py                # 统一入口
```

## 二、数据模型

### 2.1 用户与权限（RBAC）

```
User
├── id (PK)
├── username (unique)
├── email
├── hashed_password
├── full_name
├── is_active
├── created_at
└── roles → Role[] (多对多)

Role
├── id (PK)
├── name (unique): "admin", "user"
├── description
└── permissions → Permission[] (多对多)

Permission
├── id (PK)
├── code (unique): "user:create", "user:read", "user:update", "user:delete",
│                    "cad:generate", "cad:read_own", "cad:read_all",
│                    "role:manage"
└── name: "创建用户", "查看用户", ...
```

### 2.2 生成记录

```
GenerationRecord
├── id (PK)
├── user_id (FK → User)
├── model_id (SHA256 前12位)
├── prompt (用户输入的描述)
├── status: pending/llm_running/cad_running/completed/failed/cached
├── message (状态说明)
├── created_at
├── updated_at
└── file_paths: {"py": "...", "step": "...", "glb": "..."}
```

## 三、API 设计

### 3.1 Auth 模块（公共）

| 接口 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/v1/auth/register` | POST | 否 | 注册（默认 role=user） |
| `/api/v1/auth/login` | POST | 否 | 登录 |
| `/api/v1/auth/refresh` | POST | 否 | 刷新 token |
| `/api/v1/auth/me` | GET | Bearer | 当前用户信息（含 roles/permissions） |

### 3.2 CAD 模块（frontend 用）

| 接口 | 方法 | 认证 | 权限 | 说明 |
|------|------|------|------|------|
| `/api/v1/cad/generate` | POST | Bearer | cad:generate | 创建生成任务 |
| `/api/v1/cad/tasks/{task_id}` | GET | Bearer | cad:read_own | 查询任务状态 |
| `/api/v1/cad/records` | GET | Bearer | cad:read_own | **当前用户的历史记录列表** |
| `/api/v1/cad/records/{id}` | GET | Bearer | cad:read_own | 单条记录详情 |
| `/api/v1/cad/models/{model_id}/glb` | GET | Bearer | cad:read_own | 下载 GLB |
| `/api/v1/cad/models/{model_id}/step` | GET | Bearer | cad:read_own | 下载 STEP |
| `/api/v1/cad/models/{model_id}/code` | GET | Bearer | cad:read_own | 下载源码 |

### 3.3 Admin 模块（admin 用）

| 接口 | 方法 | 认证 | 权限 | 说明 |
|------|------|------|------|------|
| `/api/v1/admin/users` | GET | Bearer | user:read | 用户列表（分页） |
| `/api/v1/admin/users` | POST | Bearer | user:create | 创建用户 |
| `/api/v1/admin/users/{id}` | GET | Bearer | user:read | 用户详情 |
| `/api/v1/admin/users/{id}` | PUT | Bearer | user:update | 更新用户 |
| `/api/v1/admin/users/{id}` | DELETE | Bearer | user:delete | 删除/禁用用户 |
| `/api/v1/admin/users/{id}/roles` | PUT | Bearer | user:update | 分配角色 |
| `/api/v1/admin/roles` | GET | Bearer | role:manage | 角色列表 |
| `/api/v1/admin/roles` | POST | Bearer | role:manage | 创建角色 |
| `/api/v1/admin/roles/{id}` | PUT | Bearer | role:manage | 更新角色权限 |
| `/api/v1/admin/roles/{id}` | DELETE | Bearer | role:manage | 删除角色 |
| `/api/v1/admin/records` | GET | Bearer | cad:read_all | **所有用户的生成记录** |
| `/api/v1/admin/records?user_id=x` | GET | Bearer | cad:read_all | 指定用户的记录 |
| `/api/v1/admin/stats` | GET | Bearer | cad:read_all | 统计仪表盘 |

## 四、前端页面规划

### 4.1 Frontend（用户前台）

```
/                     → HomeView（生成页：PromptPanel + CadViewer）
/history              → HistoryView（历史记录列表：表格展示）
/history/:id          → RecordDetailView（单条记录详情 + 3D 预览）
```

**HistoryView 功能**：
- 表格：prompt、状态、创建时间、操作（预览/下载）
- 分页
- 状态筛选

### 4.2 Admin（管理后台）

```
/login                → AdminLoginView（独立登录页）
/dashboard            → DashboardView（统计卡片：用户总数/生成总数/今日生成）
/users                → UserListView（用户表格：CRUD + 分配角色）
/users/:id            → UserDetailView（用户详情 + 该用户的生成记录）
/roles                → RoleListView（角色表格：权限分配）
/records              → RecordListView（所有生成记录：可按用户筛选）
```

## 五、权限检查流程

```
1. 请求到达 → JWT 校验 → 获取 current_user
2. 检查路由的 required_permissions
3. current_user.roles → 获取所有 permissions
4. 交集检查 → 通过/返回 403
```

## 六、实施路线

### Phase 1: 后端基础（数据库 + 认证 + RBAC）
1. 定义 models（User/Role/Permission/GenerationRecord）
2. 数据库初始化 + 迁移脚本
3. JWT 认证 + 权限中间件
4. Auth API（注册/登录/me）

### Phase 2: 后端业务 API
5. CAD API（生成任务 + 记录持久化）
6. Admin API（用户/角色/记录管理）
7. 健康检查 + 统一错误处理

### Phase 3: Frontend 改造
8. 新增 /history 路由和页面
9. 对接新的 /api/v1/cad/* 接口

### Phase 4: Admin 开发
10. 登录页 + 路由守卫
11. Dashboard / Users / Roles / Records 页面
12. 对接 Admin API
