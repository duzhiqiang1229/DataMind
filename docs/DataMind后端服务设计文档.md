# DataMind 后端服务设计文档

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：明确 Integration Layer 4 适配器 + 2 配置生成器结构，更新 Airflow 作为统一执行引擎的设计

---

## 1. 文档概述

本文档用于指导 DataMind 企业智能数据中台后端服务设计与开发，实现统一业务编排、组件集成、权限管理、任务管理和数据服务能力。

**后端定位**：作为 DataMind 统一业务控制层，不替代底层数据组件能力，而负责组件 API 调用、流程编排和业务封装。

## 2. 后端总体架构

DataMind 后端采用模块化服务架构。

```
Vue 前端
    ↓
FastAPI 服务层
    ↓
业务服务模块（Service Layer）
    ↓
Integration Layer（4 适配器 + 2 配置生成器）
    ↓
Airflow / Doris / Cube / OpenMetadata（外部已部署）
```

后端负责统一接口、权限、安全和业务逻辑。

## 3. 技术选型

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12 | 开发语言 |
| FastAPI | 0.115+ | Web 框架 |
| SQLAlchemy | 2.x | 数据访问 |
| Pydantic | 2.x | 数据校验 |
| PostgreSQL | 16 | 业务数据库 |
| Redis | 7.2 | 缓存 |
| APScheduler | - | Airflow 状态轮询 |
| httpx | - | 异步 HTTP 客户端（调用组件 API） |
| cryptography | - | Fernet 凭证加密 |
| JWT | - | 认证 |

## 4. 后端工程目录设计

```
backend/
├── app/
│   ├── main.py                    # 应用入口
│   ├── core/                      # 核心配置
│   │   ├── config.py              # 环境变量配置
│   │   ├── database.py            # PostgreSQL 连接
│   │   ├── redis.py               # Redis 连接
│   │   ├── security.py            # JWT + 密码哈希 + Fernet 加密
│   │   └── dependencies.py        # 依赖注入
│   ├── api/v1/                    # 接口层
│   │   ├── auth.py                # 认证接口
│   │   ├── users.py               # 用户管理
│   │   ├── roles.py               # 角色管理
│   │   ├── menus.py               # 菜单管理
│   │   ├── components.py          # 组件连接配置
│   │   ├── datasources.py         # 数据源管理
│   │   ├── datax_tasks.py         # DataX 任务
│   │   ├── doris_query.py         # Doris 查询
│   │   ├── dashboard.py           # 首页看板
│   │   └── system.py              # 系统管理
│   ├── services/                  # 业务逻辑层
│   ├── integrations/              # 组件集成层（核心）
│   │   ├── base.py                # 适配器抽象基类
│   │   ├── airflow_client.py      # Airflow REST API
│   │   ├── doris_client.py        # Doris MySQL 协议
│   │   ├── cube_client.py         # Cube REST API
│   │   ├── openmetadata_client.py # OpenMetadata REST API
│   │   ├── datax_config_gen.py    # DataX job JSON 生成器
│   │   └── spark_config_gen.py    # Spark 作业配置生成器
│   ├── models/                    # SQLAlchemy ORM 模型
│   ├── schemas/                   # Pydantic 请求/响应模型
│   └── utils/                     # 工具类
│       └── task_scheduler.py      # Airflow 状态轮询
├── alembic/                       # 数据库迁移
├── tests/                         # 测试
├── requirements.txt
├── Dockerfile
└── .env.example
```

## 5. 服务模块设计

后端主要模块：

| 序号 | 模块 | 说明 |
|------|------|------|
| 1 | 用户权限服务 | RBAC + JWT 认证 |
| 2 | 数据源管理服务 | 数据源 CRUD + 连接测试 |
| 3 | DataX 任务管理服务 | job JSON 生成 + Airflow 触发 |
| 4 | Spark 任务管理服务 | SQL/PySpark 配置 + Airflow 触发 |
| 5 | Airflow 调度服务 | DAG 模板管理 + 状态轮询 |
| 6 | 数据模型管理服务 | 数仓模型设计 |
| 7 | Cube 指标服务 | Cube REST API 集成 |
| 8 | OpenMetadata 治理服务 | OpenMetadata REST API 集成 |
| 9 | 数据查询服务 | Doris MySQL 协议查询 |
| 10 | 数据服务 API 服务 | 对外数据接口管理 |

## 6. 用户权限服务

功能：
- 用户管理
- 角色管理
- 权限管理
- 登录认证
- 操作审计

采用 RBAC 模型：用户 → 角色 → 权限。

认证流程：登录 → 验证账号 → 生成 JWT Token → 访问接口。

## 7. 数据源管理服务

负责企业数据连接管理。

功能：
- 创建数据源
- 修改数据源
- 删除数据源
- 测试连接
- 保存连接配置

支持：Oracle、MySQL、PostgreSQL 等数据源。

## 8. DataX 集成服务

负责封装 DataX 任务管理能力。

**核心流程**：
```
用户配置源表/目标表/字段映射
    ↓
datax_config_gen.py 生成 DataX job JSON
    ↓
存入 PostgreSQL datax_tasks.job_config
    ↓
airflow_client.py 调用 Airflow REST API 触发 DAG
    ↓（传 job_json 参数给预置 DAG 模板）
Airflow 执行 datax.py
    ↓
task_scheduler.py 轮询 Airflow API 获取状态
    ↓
更新 task_instances 表状态
```

功能：
- 创建同步任务
- 生成 DataX JSON 配置（存库，不执行）
- 通过 Airflow REST API 触发执行
- 轮询获取运行状态
- 获取运行日志

## 9. Spark 任务服务

负责数据开发任务管理，支持 SQL 和 PySpark 两种模式。

功能：
- Spark 任务创建（选择 SQL 或 PySpark 模式）
- 参数配置（资源、变量等）
- 存储 SQL 文件 / PySpark 脚本到 PostgreSQL
- 通过 Airflow REST API 提交执行
- 轮询查询状态
- 获取日志

执行方式：通过 Airflow DAG 模板提交 `spark-sql`（SQL 模式）或 `spark-submit`（PySpark 模式）。

## 9.5 数据模型管理服务

负责数仓分层模型的设计和管理。

功能：
- 模型目录管理（按 ODS/DWD/DWS/ADS 分层组织）
- 表结构设计（字段名称、类型、注释、主键、分区）
- 模型 SQL 开发（建表 DDL 生成与管理）
- 模型版本管理（每次修改保存版本快照，支持回溯）
- 模型发布（将设计模型发布为 Doris 物理表）

数据流：模型设计 → 版本保存 → 发布到 Doris 执行建表。

## 9.6 发布管理服务

负责开发成果的上线发布流程管理。

功能：
- 发布任务创建（选择数据模型、Spark 任务、DataX 任务）
- 发布版本管理
- 发布执行（将对象发布到目标环境）
- 发布状态跟踪
- 发布结果记录

支持发布类型：数据模型（model）、Spark 任务（spark_task）、DataX 任务（datax_task）。

## 10. Airflow 调度服务

负责任务编排集成。

功能：
- DAG 管理（查看预置模板 DAG）
- 任务触发（REST API 传参触发）
- 状态查询（轮询 Airflow API，约 10 秒间隔）
- 日志获取（通过 Airflow API 获取日志）
- 失败重试管理

后端通过 Airflow REST API 进行调用：
- `GET /api/v1/dags` — 列出 DAG
- `POST /api/v1/dags/{dag_id}/dagRuns` — 触发执行
- `GET /api/v1/dagRuns/{run_id}` — 查询状态
- `GET /api/v1/dagRuns/{run_id}/taskInstances/logs` — 获取日志

## 11. Doris 数据服务

负责数据查询能力封装。

功能：
- SQL 查询（通过 MySQL 协议直连 Doris 端口 9030）
- 数据预览
- 查询结果转换
- 查询权限控制
- 库表元数据获取

后端使用 `pymysql` 或 `sqlalchemy` 连接 Doris，不直接暴露数据库连接给前端。

## 12. Cube 指标服务

负责指标语义能力集成。

功能：
- 指标查询（通过 Cube REST API）
- 指标模型管理
- 维度管理
- API 封装

流程：业务请求 → Cube REST API → Doris → 返回指标结果。

## 13. OpenMetadata 集成服务

负责数据治理能力集成。

功能：
- 元数据同步
- 数据目录查询
- 血缘查询
- 数据质量信息获取

通过 OpenMetadata REST API 进行交互。

## 14. 数据服务模块

提供统一数据 API 能力。

功能：
- API 创建
- API 配置
- 参数管理
- 查询转换
- 调用统计

支持业务系统、BI 和 AI 应用调用。

## 15. 接口分层设计

```
Controller 层（api/v1/）
    ↓
Service 层（services/）
    ↓
Integration 层（integrations/）
    ↓
外部组件 API
```

实现业务逻辑与组件解耦。Controller 层不直接访问数据库或组件。

## 16. 异常处理设计

统一异常体系：

| 异常类型 | HTTP 状态码 | 说明 |
|---------|------------|------|
| 业务异常 | 400 | 业务逻辑不满足 |
| 参数异常 | 422 | 参数校验失败 |
| 权限异常 | 403 | 无访问权限 |
| 未认证 | 401 | Token 缺失或过期 |
| 资源不存在 | 404 | 资源未找到 |
| 组件调用异常 | 502 | 外部组件 API 调用失败 |
| 系统异常 | 500 | 未预期的系统错误 |

统一返回错误编码和错误信息。

## 17. 日志设计

日志类型：

| 类型 | 说明 |
|------|------|
| 访问日志 | HTTP 请求记录 |
| 业务日志 | 业务操作记录 |
| 任务日志 | DataX/Spark 任务执行记录 |
| 异常日志 | 错误和异常记录 |
| 审计日志 | 用户操作审计 |

支持问题定位和运行分析。

## 18. 性能设计

优化策略：
- Redis 缓存热点数据
- 异步任务处理（APScheduler 轮询）
- 数据库连接池
- 接口分页查询
- 日志分级输出
- 服务水平扩展

## 19. 部署设计

后端服务采用 Docker 部署。

DataMind 自身部署 4 个服务：

| 服务 | 容器 | 说明 |
|------|------|------|
| FastAPI 后端 | backend | uvicorn 运行 |
| PostgreSQL | postgres | 平台元数据 |
| Redis | redis | 缓存 |
| Vue 前端 | frontend | Nginx 静态资源 |

外部组件（Airflow/Doris/Spark/Cube/OpenMetadata）已独立部署，DataMind 通过网络连接其 API。

## 20. 后续扩展

未来支持：
- 企业语义层服务
- AI Agent 服务
- 智能问数接口
- 自动化数据开发
- 智能运维能力
