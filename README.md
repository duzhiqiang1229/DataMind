# DataMind 企业智能数据平台

统一的企业数据管理、开发、治理和服务平台。通过连接六个已部署的开源组件（DataX、Spark、Airflow、Doris、Cube、OpenMetadata），提供数据源管理、数据同步、数据开发、数据仓库建模、数据查询和数据治理能力。

## 技术栈

**后端**: FastAPI 0.115 + SQLAlchemy 2.0 (async) + PostgreSQL 16 + Redis 7.2 + Alembic
**前端**: Vue 3.5 + TypeScript + Vite 6 + Element Plus + Pinia + ECharts
**调度**: Airflow (REST API) + DataX (同步) + Spark (计算)
**存储**: Doris (OLAP) + Cube (语义层) + OpenMetadata (元数据)

## 目录结构

```
DataMind/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── core/           # 配置、数据库、Redis、安全、依赖注入
│   │   ├── api/v1/         # 10 个 API 路由模块
│   │   ├── services/       # 11 个业务逻辑服务
│   │   ├── integrations/   # 7 个组件适配器
│   │   ├── models/         # 9 个 ORM 模型文件 (21 张表)
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── utils/          # APScheduler 定时轮询
│   │   └── seed_data.py    # 幂等种子数据 (admin 用户/角色/权限/菜单)
│   ├── alembic/            # 数据库迁移
│   ├── tests/              # pytest 测试 (38 单元 + 11 集成)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── frontend/               # Vue 3 前端
│   └── src/
│       ├── views/          # 6 个页面 (login/dashboard/datasource/datax/query/system)
│       ├── api/            # Axios 封装 + API 模块
│       ├── stores/         # Pinia 状态管理
│       ├── router/         # Vue Router (含鉴权守卫)
│       └── layouts/        # 主布局
├── airflow-dags/           # Airflow DAG 模板 (DataX + Spark)
├── database/               # SQL 脚本
│   ├── 001_init_schema.sql       # PostgreSQL DDL
│   └── 002_doris_warehouse_init.sql  # Doris 数仓初始化 (ODS/DWD/DWS/ADS)
├── docs/                   # 14 篇设计文档
└── TECH_DESIGN.md          # 技术设计文档
```

## 快速开始

### 方式一: Docker Compose (推荐)

```bash
# 1. 在项目根目录准备生产配置
cp backend/.env.example backend/.env
cp openmetadata/.env.example openmetadata/.env
# 必须设置随机 JWT_SECRET_KEY、有效 Fernet ENCRYPTION_KEY、
# 强 DB_PASSWORD/REDIS_PASSWORD，以及至少 24 位的随机 EXECUTOR_TOKEN。
# 同时替换 openmetadata/.env 中的数据库密码、管理员密码和两个 Fernet Key；
# 两个 Fernet Key 在产生加密数据后必须保持稳定。
# 首次部署还应设置：
# BOOTSTRAP_ADMIN=true
# INITIAL_ADMIN_PASSWORD=<至少 12 位的强密码>

# 2. 构建并启动。后端入口会自动执行 Alembic 迁移；
# BOOTSTRAP_ADMIN=true 时会幂等初始化管理员、角色、权限和菜单。
docker compose -f docker-compose.prod.yml up -d --build

# 3. 检查服务
docker compose -f docker-compose.prod.yml ps
# 前端: http://localhost/
# 健康检查: http://localhost:8000/health

# 4. OpenMetadata 已包含在主 Compose 中，无需启动第二个项目。
# 首次启动会额外下载较大的 OpenMetadata 官方镜像。
# OpenMetadata: http://localhost:8585
# 启动后在「系统管理 → 组件配置」中保存 Bot JWT Token。
```

OpenMetadata 与 DataMind 共用同一个 PostgreSQL 实例，但分别使用 `openmetadata_db`、
`airflow_db` 和 `datamind` 三个独立数据库；首次启动会自动创建前两个数据库及专用账号。
Elasticsearch 继续提供资产搜索、筛选和聚合。
当前单机配置用于试运行；生产环境应参照官方容量要求拆分部署、轮换管理员和 JWT 密钥，
并为 DataMind 配置最小权限 Bot。

### 方式二: 本地开发

#### 前置条件

- Python 3.12+
- Node.js 18+
- PostgreSQL 16 (本地或 Docker)
- Redis 7 (本地或 Docker)

#### 后端

```bash
cd backend

# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 2. 安装依赖
pip install -r requirements-dev.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env, 填入你的 PostgreSQL/Redis 连接信息

# 4. 数据库迁移
alembic upgrade head

# 5. 初始化种子数据
python -m app.seed_data

# 6. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
# 访问 http://localhost:5173

# 3. 生产构建
npm run build
```

## 数据库迁移 (Alembic)

```bash
cd backend

# 生成新迁移 (修改模型后)
alembic revision --autogenerate -m "描述变更内容"

# 应用迁移到数据库
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

## 测试

```bash
cd backend

# 运行单元测试 (无需 PostgreSQL/Redis)
pytest

# 运行集成测试 (需要 PostgreSQL + Redis 运行中)
pytest -m integration

# 运行所有测试
pytest -m ""

# 查看测试覆盖率
pytest --cov=app --cov-report=term-missing
```

## 初始管理员

生产环境不再提供默认密码。首次启动前，在 `backend/.env` 中设置
`BOOTSTRAP_ADMIN=true`、`INITIAL_ADMIN_USERNAME` 和至少 12 位的
`INITIAL_ADMIN_PASSWORD`。初始化成功后可将 `BOOTSTRAP_ADMIN` 改回 `false`。

## 开发计划

项目按 7 个 Sprint 推进, 详见 `docs/DataMind开发实施计划与项目里程碑.md`:

1. Sprint 1: 基础门户 + RBAC + 集成层 (进行中)
2. Sprint 2: DataX → Doris 数据同步
3. Sprint 3: Spark + Airflow 数据开发
4. Sprint 4: Doris 建模 + SQL 工作台
5. Sprint 5: Cube 指标层
6. Sprint 6: OpenMetadata 数据治理
7. Sprint 7: 生产发布
