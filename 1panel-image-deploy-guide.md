# Text-to-CAD 1Panel 镜像部署指南（小白版）

> 核心思路：**在本地 Windows 电脑把 Docker 镜像构建好**，导出成文件，上传到服务器直接运行。
>
> 服务器上不需要安装 Node.js、Python 开发环境，也不需要传源代码。

---

## 前置条件

### 本地（你的 Windows 电脑）
- 已安装 **Docker Desktop**（https://www.docker.com/products/docker-desktop）
- Docker Desktop 已启动

### 服务器
- 一台 Linux 服务器（Ubuntu / CentOS 等）
- 已安装 **1Panel**（https://1panel.cn）
- 服务器已安装 Docker（1Panel 自带）

---

## 第一部分：在本地 Windows 构建镜像

### 步骤 1：打开 PowerShell

在 Windows 搜索框输入 `PowerShell`，右键「以管理员身份运行」。

### 步骤 2：进入项目目录

```powershell
cd e:/Code/text-to-cad
```

### 步骤 3：修改 .env（关键！）

打开文件：`e:/Code/text-to-cad/web-app/backend/.env`

把 `VITE_API_BASE` 改成你服务器的**公网 IP**：

```env
OPENAI_API_KEY=你的API密钥
OPENAI_BASE_URL=https://api.lkeap.cloud.tencent.com/coding/v3
LLM_MODEL=kimi-k2.5
SECRET_KEY=你自己编一个20位以上的随机字符串
VITE_API_BASE=http://123.45.67.89:8000
```

> **注意**：`123.45.67.89` 换成你服务器的真实公网 IP！
>
> 这个地址会在构建时写进前端代码，构建后就不能改了。

### 步骤 4：构建三个 Docker 镜像

在 PowerShell 中依次执行下面三条命令：

```powershell
# 构建后端镜像
docker build -f web-app/Dockerfile.backend -t ttc-backend:latest .

# 构建用户端镜像
docker build -f web-app/Dockerfile.frontend -t ttc-frontend:latest .

# 构建管理后台镜像
docker build -f web-app/Dockerfile.admin -t ttc-admin:latest .
```

每条命令可能需要 5-15 分钟，请耐心等待。看到 `Successfully tagged ...` 就是成功了。

### 步骤 5：导出镜像为文件

```powershell
# 创建输出目录
mkdir e:/ttc-deploy

# 导出三个镜像
docker save ttc-backend:latest -o e:/ttc-deploy/ttc-backend.tar
docker save ttc-frontend:latest -o e:/ttc-deploy/ttc-frontend.tar
docker save ttc-admin:latest -o e:/ttc-deploy/ttc-admin.tar
```

导出完成后，`e:/ttc-deploy/` 文件夹下会有三个 `.tar` 文件。

---

## 第二部分：上传文件到服务器

### 步骤 6：创建服务器目录

在 1Panel 中操作：

1. 打开 1Panel → 文件
2. 进入 `/opt` 目录
3. 点击「新建文件夹」，命名为 `ttc-deploy`
4. 进入 `ttc-deploy`，再新建一个 `data` 文件夹

### 步骤 7：上传镜像文件

在 1Panel 文件管理中：

1. 进入 `/opt/ttc-deploy`
2. 点击「上传」
3. 把下面 5 个文件从 `e:/ttc-deploy/` 上传到服务器：
   - `ttc-backend.tar`
   - `ttc-frontend.tar`
   - `ttc-admin.tar`

同时上传这两个部署配置文件（在本文档同级目录中）：
   - `deploy-runtime.yml`
   - `deploy-env-example.env`

> 上传方式：直接把文件拖到浏览器窗口，或用「上传」按钮选择文件。

### 步骤 8：上传完成后重命名 .env

在 1Panel 文件管理中：

1. 找到 `/opt/ttc-deploy/deploy-env-example.env`
2. 重命名为 `.env`
3. 双击编辑 `.env`，把 `VITE_API_BASE` 改成你服务器的公网 IP

---

## 第三部分：在服务器上导入并运行

### 步骤 9：打开 1Panel 终端

1Panel → 主机 → 终端，点击「连接」。

### 步骤 10：导入 Docker 镜像

在终端中执行：

```bash
cd /opt/ttc-deploy

docker load < ttc-backend.tar
docker load < ttc-frontend.tar
docker load < ttc-admin.tar
```

导入完成后，验证镜像是否存在：

```bash
docker images | grep ttc
```

应该看到三行输出，分别是 `ttc-backend`、`ttc-frontend`、`ttc-admin`。

### 步骤 11：启动服务

```bash
cd /opt/ttc-deploy

docker compose -f deploy-runtime.yml --env-file .env up -d
```

参数说明：
- `-f deploy-runtime.yml`：使用运行版配置（不重新构建）
- `--env-file .env`：读取环境变量
- `-d`：后台运行

### 步骤 12：查看运行状态

```bash
docker compose -f deploy-runtime.yml ps
```

看到三个容器都是 `running` 状态，说明启动成功。

---

## 第四部分：放行端口 + 访问

### 步骤 13：放行端口

**A. 云服务器安全组**（阿里云/腾讯云/华为云控制台）

添加三条入方向规则：

| 协议 | 端口范围 | 来源 |
|------|----------|------|
| TCP | 8000 | 0.0.0.0/0 |
| TCP | 3000 | 0.0.0.0/0 |
| TCP | 3001 | 0.0.0.0/0 |

**B. 服务器防火墙**（1Panel 中操作）

1Panel → 主机 → 防火墙 → 添加规则，同样放行 8000、3000、3001。

### 步骤 14：验证访问

在浏览器中输入：

| 服务 | 地址 |
|------|------|
| 用户端 | `http://你的服务器IP:3000` |
| 管理后台 | `http://你的服务器IP:3001` |
| API 健康检查 | `http://你的服务器IP:8000/api/health` |

如果 API 返回 JSON（包含 `"ok": true`），说明全部正常。

---

## 第五部分（可选）：配置域名 + HTTPS

### 步骤 15：域名解析

在域名服务商添加三条 A 记录：

| 主机记录 | 记录值（服务器公网IP）|
|----------|----------------------|
| `www` | 123.45.67.89 |
| `api` | 123.45.67.89 |
| `admin` | 123.45.67.89 |

### 步骤 16：1Panel 创建反向代理网站

1Panel → 网站 → 创建网站 → 反向代理

创建三个：

**1. 用户端**
- 主域名：`www.yourdomain.com`
- 代理地址：`http://127.0.0.1:3000`
- 开启 HTTPS（1Panel 自动申请 Let's Encrypt 证书）

**2. 后端 API**
- 主域名：`api.yourdomain.com`
- 代理地址：`http://127.0.0.1:8000`
- 开启 HTTPS

**3. 管理后台**
- 主域名：`admin.yourdomain.com`
- 代理地址：`http://127.0.0.1:3001`
- 开启 HTTPS

### 步骤 17：更新 API 地址（重要！）

配好 HTTPS 域名后，需要**重新构建前端镜像**：

1. 回到本地 Windows，修改 `.env`：

```env
VITE_API_BASE=https://api.yourdomain.com
```

2. 重新构建 `ttc-frontend` 和 `ttc-admin`：

```powershell
cd e:/Code/text-to-cad

docker build -f web-app/Dockerfile.frontend -t ttc-frontend:latest .
docker build -f web-app/Dockerfile.admin -t ttc-admin:latest .

docker save ttc-frontend:latest -o e:/ttc-deploy/ttc-frontend.tar
docker save ttc-admin:latest -o e:/ttc-deploy/ttc-admin.tar
```

3. 上传新的 `ttc-frontend.tar` 和 `ttc-admin.tar` 到服务器 `/opt/ttc-deploy`

4. 在 1Panel 终端执行：

```bash
cd /opt/ttc-deploy

docker compose -f deploy-runtime.yml down

docker load < ttc-frontend.tar
docker load < ttc-admin.tar

docker compose -f deploy-runtime.yml --env-file .env up -d
```

---

## 常用命令速查

```bash
# 查看运行状态
docker compose -f deploy-runtime.yml ps

# 查看日志
docker compose -f deploy-runtime.yml logs -f

# 只看后端日志
docker compose -f deploy-runtime.yml logs -f backend

# 停止服务
docker compose -f deploy-runtime.yml down

# 重启服务
docker compose -f deploy-runtime.yml restart

# 进入后端容器内部（调试用）
docker exec -it ttc-backend bash
```

---

## 数据持久化说明

| 数据 | 服务器路径 | 说明 |
|------|-----------|------|
| 数据库 | `/opt/ttc-deploy/data/app.db` | SQLite 数据库，用户/生成记录都在这里 |
| 生成模型 | `/opt/ttc-deploy/data/generated_models` | 用户生成的 CAD 文件 |

这两个目录已通过 `volumes` 挂载到宿主机，**删除容器不会丢失数据**。

建议定期备份 `/opt/ttc-deploy/data/` 文件夹。

---

## 常见问题

### Q1：构建时报错 `no such file or directory`？
- 确认你在 `e:/Code/text-to-cad` 目录下执行命令
- 确认 Dockerfile 路径正确：`web-app/Dockerfile.backend`

### Q2：导入镜像时说 `archive/tar: invalid tar header`？
- 可能是上传过程中文件损坏，重新上传 tar 文件
- 或者本地导出时Docker没完成就中断了，重新执行 `docker save`

### Q3：服务启动了但访问不了？
- 检查安全组和防火墙是否放行了对应端口
- 检查 `.env` 里的 `VITE_API_BASE` 是否配置正确
- 浏览器 F12 → Network 看请求地址对不对

### Q4：怎么创建管理员？
- 先在用户端注册一个账号
- 1Panel 终端执行下面的命令：

```bash
docker exec -it ttc-backend bash
python -c "
from app.db.database import SessionLocal
from app.crud.user import get_user_by_username, update_user
db = SessionLocal()
u = get_user_by_username(db, '你的用户名')
update_user(db, u, {'is_superuser': True})
print('已设为管理员')
"
exit
```

### Q5：怎么更新代码？
- 在本地修改代码 → 重新构建镜像 → 导出 tar → 上传 → 导入 → 重启容器
- 如果只是后端代码改了，只需要重建 `ttc-backend` 镜像
