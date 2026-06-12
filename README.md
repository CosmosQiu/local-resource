# AI Resource Hub

公司内部 AI 资源管理平台 — AI 账号/API Key 管理 + GPU 算力监控调度 + 容器/裸金属申请分配 + 大屏展示。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python FastAPI + SQLAlchemy 2.0 async + PostgreSQL 15 |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + ECharts |
| 认证 | JWT (access + refresh) + Casbin RBAC |
| 加密 | AES-256-GCM (Fernet) — API Key 落盘加密 |
| 任务队列 | Celery + Redis (Cookie 到期检测) |
| GPU 监控 | GPUStack 集成（可选） + Ansible 补充 |
| 测试 | pytest + pytest-asyncio + httpx |

## 快速启动

### 1. 环境准备

```bash
# 启动 PostgreSQL + Redis
docker compose up -d

# 配置环境变量
cp .env.example .env   # 修改 JWT_SECRET_KEY 和 VAULT_ENCRYPTION_KEY
```

### 2. 后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head      # 创建表 + 种子数据
uvicorn app.main:app --reload   # http://localhost:8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173
```

## API 路由 (31 endpoints)

| 前缀 | 端点 | 权限 |
|---|---|---|
| `/api/health` | `GET /` | 公开 |
| `/api/auth` | `POST /login`, `/register`, `/refresh`, `/change-password`, `GET /me` | 注册公开，其余需认证 |
| `/api/accounts` | `GET/POST /`, `GET/PUT/DELETE /{id}`, `GET /{id}/secret` | accounts.read/create/update/delete/read_secret |
| `/api/compute` | `GET/POST /`, `GET/PUT/DELETE /{id}` | compute.read/manage |
| `/api/compute/requests` | `GET/POST /`, `GET /{id}`, `POST /{id}/approve`, `POST /{id}/stop` | compute.request/approve |
| `/api/dashboard` | `GET /summary` | dashboard.view |
| `/api/admin` | `GET /users`, `PUT /users/{id}/roles`, `GET /roles`, `GET /permissions` | admin.manage_users/manage_roles |

## 预置角色

| 角色 | 权限 |
|---|---|
| **admin** | 全部权限 |
| **operator** | 账号读写 + 算力管理 + 审批 + 大屏 |
| **viewer** | 只读：账号列表 + 算力 + 大屏 |
| **user** | 算力查看 + 申请 + 大屏 |

## 数据库模型

- `users` / `roles` / `permissions` — 用户与 RBAC
- `ai_accounts` — AI 平台账号（加密存储凭证 + cookie_data）
- `compute_resources` — 异构算力资源（裸金属/K8s/Linux/Windows + GPUStack 集成）
- `compute_resource_gpus` — GPU 指标时间序列
- `container_requests` — 容器/裸金属申请 → 审批 → 运行 → 到期

## 测试

```bash
cd backend
pytest tests/ -v
```

## 项目结构

```
ai-resource-hub/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/          # auth/accounts/compute/dashboard/admin 路由
│   │   ├── core/         # config/database/security/casbin/celery
│   │   ├── models/       # user/account/compute/container
│   │   ├── schemas/      # Pydantic 校验
│   │   ├── services/     # 业务逻辑
│   │   └── tasks/        # Celery 异步任务
│   ├── alembic/          # 数据库迁移
│   └── tests/            # pytest
└── frontend/
    └── src/
        ├── api/client.ts # Axios + JWT 拦截器
        ├── stores/auth.ts
        ├── router/       # 路由守卫 + 权限过滤
        └── views/        # Login/Layout/Dashboard/Accounts/Compute/Requests/Admin
```
