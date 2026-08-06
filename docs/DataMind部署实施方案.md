# DataMind 企业智能平台部署实施方案

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：更新为 DataMind 仅自部署 4 个服务，外部组件已独立部署通过 API 连接

---

## 1. 文档概述

本文档用于指导 DataMind 企业智能平台的环境规划、部署实施、服务配置、运行维护和生产上线。

**建设目标**：通过 API 连接已部署的 DataX、Spark、Airflow、Doris、Cube、OpenMetadata 等组件，建设稳定、可扩展的数据平台。

**核心原则**：DataMind 不部署底层组件，自身仅部署 Vue 前端 + FastAPI 后端 + PostgreSQL + Redis。

## 2. 部署总体架构

采用分层部署架构：

| 层级 | 组件 | 部署方 |
|------|------|--------|
| 访问层 | Nginx、Vue 前端门户 | DataMind |
| 业务服务层 | FastAPI 后台服务 | DataMind |
| 基础设施层 | PostgreSQL、Redis | DataMind |
| 外部数据平台层 | DataX、Spark、Airflow、Doris、Cube、OpenMetadata | 外部已部署 |

## 3. DataMind 自部署服务

### 4 个服务容器

| 服务 | 容器 | 端口 | 说明 |
|------|------|------|------|
| Vue 前端 | frontend | 80 (Nginx) | 静态资源 + 反向代理 |
| FastAPI 后端 | backend | 8000 | uvicorn 运行 |
| PostgreSQL | postgres | 5432 | 平台元数据 |
| Redis | redis | 6379 | 缓存 |

### Docker Compose 配置

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://datamind:xxx@postgres:5432/datamind
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=datamind
      - POSTGRES_USER=datamind
      - POSTGRES_PASSWORD=xxx
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./database/001_init_schema.sql:/docker-entrypoint-initdb.d/01-init.sql

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

## 4. 外部组件连接配置

外部组件已独立部署，DataMind 通过系统管理界面配置连接信息：

| 组件 | 连接方式 | 配置内容 |
|------|---------|---------|
| Airflow | REST API | `http://{host}:8080/api/v1/` + Token |
| Doris | MySQL 协议 | `{host}:9030` + 用户名密码 |
| Cube | REST API | `http://{host}:4000/cubejs-api/v1/` + API Token |
| OpenMetadata | REST API | `http://{host}:8585/api/v1/` + JWT Token |
| DataX | Airflow 执行 | 无直接连接（通过 Airflow DAG 执行 CLI） |
| Spark | Airflow 执行 | 无直接连接（通过 Airflow DAG 提交） |

连接信息存储在 PostgreSQL `component_configs` 表，使用 Fernet 加密敏感信息。

## 5. 基础环境准备

操作系统推荐：Ubuntu Server 24.04 LTS

基础软件：
- Docker 27.x
- Docker Compose 2.x
- Python 3.12（开发用）
- Node.js 22 LTS（构建前端用）

网络要求：DataMind 服务器需能访问外部组件的 API 端口。

## 6. 前端部署

技术：Vue 3.5 + TypeScript

部署流程：
1. 安装 Node 环境
2. `npm install` 安装依赖
3. `npm run build` 构建生产包
4. 使用 Nginx 发布静态资源 + 反向代理后端 API

访问路径：用户 → Nginx → Vue 门户 → FastAPI 后端 → 外部组件 API

## 7. 后端服务部署

技术：FastAPI + uvicorn

部署内容：
- 用户权限服务
- 数据源管理服务
- DataX 管理服务（配置生成 + Airflow 触发）
- Spark 管理服务（配置生成 + Airflow 触发）
- Airflow 接口服务
- Doris 查询服务
- Cube 接口服务
- OpenMetadata 接口服务
- 组件连接配置管理
- Airflow 状态轮询调度器

通过 Docker 容器运行，配置环境变量连接 PostgreSQL、Redis 和外部组件。

## 8. Airflow DAG 模板部署

### 预置 DAG 模板文件

| 模板 | 用途 |
|------|------|
| `datax_sync_dag.py` | DataX 数据同步 DAG（接收 job_json 参数） |
| `spark_job_dag.py` | Spark 作业 DAG（支持 SQL 和 PySpark 模式） |

### 部署方式

将 DAG 模板文件复制到 Airflow 的 `dags/` 目录，Airflow 自动加载。

DataMind 通过 REST API 触发 DAG 执行时传入参数：
- DataX DAG：传 `job_json` 参数
- Spark DAG：传 `sql_content` 或 `script_content` + `submit_params` 参数

## 9. 网络规划

```
用户
  ↓
Nginx (80/443)
  ↓
DataMind 后端 (8000)
  ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Airflow API  │ Doris MySQL  │ Cube API     │ OpenMetadata │
│ (8080)       │ (9030)       │ (4000)       │ (8585)       │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

需要开放的端口：
- HTTP/HTTPS：用户访问
- 8000：后端 API（内部）
- 外部组件 API 端口（从 DataMind 后端访问）

## 10. 数据备份方案

备份对象：
- PostgreSQL 业务数据库
- 配置文件（.env、docker-compose.yml）
- Airflow DAG 模板文件
- Cube 模型文件

采用定期备份和异地保存策略。

## 11. 监控运维方案

监控内容：
- DataMind 服务状态（frontend、backend、postgres、redis）
- 外部组件 API 连接状态
- 任务运行状态（通过 Airflow API）
- 数据同步情况
- 查询性能

可扩展 Prometheus + Grafana 监控体系。

## 12. 上线实施流程

| 阶段 | 内容 |
|------|------|
| 阶段一 | 环境准备（Docker、网络） |
| 阶段二 | DataMind 4 服务部署 |
| 阶段三 | 组件连接配置（通过 UI 配置外部组件地址） |
| 阶段四 | Airflow DAG 模板部署 |
| 阶段五 | Doris 数仓分层初始化 |
| 阶段六 | 数据链路测试 |
| 阶段七 | 业务验收 |
| 阶段八 | 正式运行 |

## 13. 推荐服务器规划

### 开发环境

单机 Docker Compose 部署 DataMind 4 个服务，连接开发环境的外部组件。

### 测试环境

多容器部署，模拟生产环境。

### 生产环境

| 服务器 | 部署内容 |
|--------|---------|
| 应用服务器 | DataMind 前端 + 后端 + PostgreSQL + Redis |
| （外部组件） | Doris/Airflow/Spark/Cube/OpenMetadata（已独立部署） |

## 14. 后续扩展规划

未来增加：
- 企业语义层
- 知识图谱
- AI Agent
- 智能问数
- 自动化数据开发能力

形成企业智能数据平台。
