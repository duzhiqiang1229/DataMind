# DataMind 代码工程设计规范

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：更新后端工程结构，明确 Integration Layer 4 适配器 + 2 配置生成器结构，补充 Airflow DAG 模板规范

---

## 1. 文档概述

本文档用于规范 DataMind 企业智能数据中台的软件研发过程，包括后端 Python 开发、前端 Vue 开发、数据库设计、接口开发、代码管理、日志规范、异常处理和部署规范。

**目标**：建立统一、可维护、可扩展的软件工程体系。

## 2. 工程设计原则

1. **模块化设计**：功能按照业务领域拆分
2. **分层设计**：接口层、业务层、数据层、集成层分离
3. **高内聚低耦合**：减少模块之间依赖
4. **配置与代码分离**：组件连接信息存储于数据库，通过 UI 管理
5. **自动化优先**：支持 CI/CD 和自动部署
6. **可观测性**：日志、监控、异常可追踪

## 3. Git 代码管理规范

采用 Git 进行代码版本管理。

分支设计：

| 分支 | 用途 |
|------|------|
| `main` | 生产稳定版本 |
| `develop` | 开发集成版本 |
| `feature/*` | 功能开发分支 |
| `bugfix/*` | 问题修复分支 |
| `release/*` | 发布准备分支 |

提交规范：

| 类型 | 含义 |
|------|------|
| `feat` | 新增功能 |
| `fix` | 修复问题 |
| `refactor` | 代码重构 |
| `docs` | 文档修改 |
| `chore` | 工程配置修改 |

## 4. 后端 Python 工程规范

技术栈：
- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Pydantic 2.x
- APScheduler（任务轮询）

目录规范：

```
backend/
├── app/
│   ├── main.py              # 应用入口
│   ├── core/                # 核心配置
│   │   ├── config.py        # 环境配置
│   │   ├── database.py      # 数据库连接
│   │   ├── redis.py         # Redis 连接
│   │   ├── security.py      # JWT + 密码哈希 + 凭证加密
│   │   └── dependencies.py  # 依赖注入
│   ├── api/v1/              # 接口层（路由）
│   │   ├── auth.py          # 认证
│   │   ├── users.py         # 用户管理
│   │   ├── roles.py         # 角色管理
│   │   ├── menus.py         # 菜单管理
│   │   ├── components.py    # 组件连接配置
│   │   ├── datasources.py   # 数据源管理
│   │   ├── datax_tasks.py   # DataX 任务
│   │   ├── spark_tasks.py   # Spark 任务
│   │   ├── data_models.py   # 数据模型管理
│   │   ├── publish.py       # 发布管理
│   │   ├── doris_query.py   # Doris 查询
│   │   ├── dashboard.py     # 首页看板
│   │   └── system.py        # 系统管理
│   ├── services/            # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── datasource_service.py
│   │   ├── datax_task_service.py
│   │   ├── spark_task_service.py
│   │   ├── data_model_service.py  # 数据模型管理
│   │   ├── publish_service.py     # 发布管理
│   │   ├── doris_query_service.py
│   │   └── system_service.py
│   ├── integrations/        # 组件集成层（核心）
│   │   ├── base.py          # 适配器抽象基类
│   │   ├── airflow_client.py    # Airflow REST API 适配器
│   │   ├── doris_client.py      # Doris MySQL 协议适配器
│   │   ├── cube_client.py       # Cube REST API 适配器
│   │   ├── openmetadata_client.py  # OpenMetadata REST API 适配器
│   │   ├── datax_config_gen.py  # DataX job JSON 生成器
│   │   └── spark_config_gen.py  # Spark 作业配置生成器
│   ├── models/              # 数据模型（SQLAlchemy ORM）
│   ├── schemas/            # 请求响应模型（Pydantic）
│   └── utils/              # 工具类
│       └── task_scheduler.py    # Airflow 状态轮询调度器
├── alembic/                # 数据库迁移
├── tests/                  # 测试
├── requirements.txt
├── Dockerfile
└── .env.example
```

## 5. 后端分层规范

| 层级 | 职责 | 规则 |
|------|------|------|
| Controller 层（api） | HTTP 请求接收和参数校验 | 禁止直接访问数据库 |
| Service 层（services） | 业务逻辑处理 | 可调用 Integration 层 |
| Integration 层（integrations） | 外部组件 API 调用 | 6 大组件适配器 |
| Model 层（models） | 数据库 ORM 模型 | 数据访问统一通过 Service 层 |

### Integration 层说明

Integration Layer 是 DataMind 架构的核心，包含：

| 模块 | 类型 | 说明 |
|------|------|------|
| `airflow_client.py` | REST API 适配器 | DAG 列表、触发、状态查询、日志获取 |
| `doris_client.py` | MySQL 协议适配器 | SQL 查询、库表管理 |
| `cube_client.py` | REST API 适配器 | 指标查询、模型元数据 |
| `openmetadata_client.py` | REST API 适配器 | 数据目录、血缘、质量 |
| `datax_config_gen.py` | 配置生成器 | 生成 DataX job JSON（存库，不执行） |
| `spark_config_gen.py` | 配置生成器 | 生成 Spark 作业配置 + 管理 SQL/脚本文件（存库，不执行） |

## 6. Python 编码规范

遵循 PEP 8 规范。

要求：
- 使用类型注解
- 函数职责单一
- 避免重复代码
- 公共方法抽取工具类
- 关键逻辑添加注释

命名规范：

| 对象 | 规范 | 示例 |
|------|------|------|
| 变量和函数 | snake_case | `get_dag_status` |
| 类 | PascalCase | `AirflowClient` |
| 常量 | UPPER_SNAKE | `MAX_RETRIES` |

## 7. FastAPI 接口开发规范

接口设计遵循 RESTful 规范。

路径规范：

| 方法 | 用途 |
|------|------|
| GET | 查询 |
| POST | 创建 |
| PUT | 更新 |
| DELETE | 删除 |

统一返回格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

分页返回格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

接口必须包含参数校验、异常处理和接口文档（OpenAPI/Swagger）。

## 8. 数据库开发规范

数据库：PostgreSQL 16

规范：
- 表名使用 snake_case
- 字段名称清晰
- 必须设计主键
- 重要字段增加索引
- 时间字段统一使用 `created_at` / `updated_at`
- 禁止在业务代码中编写复杂 SQL
- JSON 配置使用 JSONB 类型

数据访问统一通过 Service 层。

## 9. SQL 开发规范

要求：
- SQL 格式统一
- 关键字段换行
- 避免 `SELECT *`
- 大表查询必须考虑性能
- SQL 增加必要注释

数据仓库 SQL 需遵循 ODS/DWD/DWS/ADS 分层规范。先建分层结构，使用模拟数据验证链路。

## 10. Airflow DAG 模板规范

DataMind 采用**预置模板 + 参数触发**模式，不动态生成 DAG 代码。

### DAG 模板文件

| 模板文件 | 用途 |
|---------|------|
| `datax_sync_dag.py` | DataX 数据同步 DAG，接收 `job_json` 参数 |
| `spark_job_dag.py` | Spark 作业 DAG，支持 SQL 模式和 PySpark 模式 |

### 参数传递方式

- DataMind 通过 Airflow REST API 的 `POST /dags/{dag_id}/dagRuns` 传参触发
- DAG 模板接收 `conf` 参数，从中获取配置
- DataX：接收 `job_json` 参数，写入临时文件执行 `datax.py`
- Spark：接收 `sql_content` 或 `script_content` + `submit_params`，执行 `spark-sql` 或 `spark-submit`

## 11. Vue 前端工程规范

技术栈：
- Vue 3.5
- TypeScript 5
- Element Plus
- ECharts
- Pinia（状态管理）

目录：

```
frontend/src/
├── api/           # 接口封装
├── assets/        # 静态资源
│   └── styles/     # 全局样式
├── components/     # 公共组件
├── layouts/        # 布局组件
├── router/         # 路由
├── stores/         # Pinia 状态管理
├── types/          # TypeScript 类型定义
├── utils/          # 工具类
└── views/          # 页面
    ├── login/       # 登录
    ├── dashboard/   # 首页驾驶舱
    ├── datasource/  # 数据源管理
    ├── datax/       # DataX 任务
    ├── query/       # SQL 工作台
    └── system/      # 系统管理
```

## 12. 前端开发规范

要求：
- 页面组件化
- 公共组件复用
- API 调用统一管理（通过 `api/` 模块封装 Axios）
- 禁止页面直接写复杂业务逻辑
- 路由守卫校验 JWT Token
- Axios 拦截器统一注入 Token + 401 自动跳转

组件命名使用 PascalCase。

## 13. DataMind 组件集成规范

外部组件统一通过 Integration 层调用。

| 组件 | 集成方式 | 说明 |
|------|---------|------|
| Airflow | REST API | DAG 管理、触发、状态、日志 |
| Doris | MySQL 协议 | SQL 查询、库表管理 |
| Cube | REST API | 指标查询、模型元数据 |
| OpenMetadata | REST API | 数据目录、血缘、质量 |
| DataX | 配置生成 + Airflow 执行 | DataMind 生成 job JSON，Airflow DAG 执行 |
| Spark | 配置生成 + Airflow 执行 | DataMind 生成配置，Airflow DAG 执行 |

组件连接信息存储在 PostgreSQL `component_configs` 表，通过系统管理 UI 管理。

## 14. 日志规范

日志分级：

| 级别 | 用途 |
|------|------|
| DEBUG | 调试信息 |
| INFO | 正常运行信息 |
| WARNING | 警告信息 |
| ERROR | 错误信息 |

日志必须包含：时间、用户、请求 ID、模块、错误信息。

## 15. 异常处理规范

异常分类：

| 类型 | 说明 |
|------|------|
| 业务异常 | 业务逻辑不满足条件 |
| 参数异常 | 请求参数校验失败 |
| 权限异常 | 无访问权限 |
| 组件调用异常 | 外部组件 API 调用失败 |
| 系统异常 | 未预期的系统错误 |

禁止直接返回底层异常信息。

## 16. 配置管理规范

配置与代码分离。

配置内容：
- 数据库连接（环境变量）
- Redis 配置（环境变量）
- 密钥信息（环境变量）
- **第三方组件连接信息**（数据库 `component_configs` 表 + UI 管理）

敏感信息（密码、Token）使用 Fernet 加密存储。

## 17. Docker 开发规范

要求：
- 一个服务一个容器
- 使用固定版本镜像
- 不在镜像中保存敏感信息
- 使用 docker-compose 管理开发环境

DataMind 自身部署 4 个容器：frontend、backend、postgres、redis。外部组件（Doris/Airflow/Spark/Cube/OpenMetadata）已独立部署，不在 DataMind 的 Docker Compose 中。

## 18. 测试规范

测试类型：

| 类型 | 说明 |
|------|------|
| 单元测试 | 验证函数逻辑 |
| 接口测试 | 验证 API |
| 集成测试 | 验证组件交互 |

核心模块必须具备测试用例。Integration 层需要 Mock 外部组件 API 进行测试。

## 19. CI/CD 规范

流程：

```
代码提交 → 自动测试 → 构建镜像 → 部署测试环境 → 发布生产环境
```

## 20. DataMind 研发规范总结

所有代码遵循：
- 统一架构
- 统一代码风格
- 统一接口规范
- 统一日志体系
- 统一部署方式

保证 DataMind 长期稳定演进。
