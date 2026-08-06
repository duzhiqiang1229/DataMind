# DataMind Backend

## 工程结构

```
backend/
├── app/
│   ├── main.py                     # FastAPI 应用入口
│   ├── core/                       # 核心模块
│   │   ├── config.py               #   Pydantic Settings 配置
│   │   ├── database.py             #   SQLAlchemy 异步引擎/会话
│   │   ├── redis.py                #   Redis 连接
│   │   ├── security.py             #   JWT/密码哈希/凭证加密
│   │   └── dependencies.py         #   FastAPI 依赖注入(get_current_user, 分页)
│   ├── api/                        # API 路由层
│   │   ├── router.py               #   路由聚合
│   │   └── v1/                     #   v1 版本接口
│   │       ├── auth.py             #     登录/刷新/当前用户
│   │       ├── users.py            #     用户 CRUD
│   │       ├── roles.py            #     角色 CRUD + 权限分配
│   │       ├── menus.py            #     菜单管理
│   │       ├── components.py       #     组件连接配置 CRUD + 健康检查
│   │       ├── datasources.py      #     数据源 CRUD + 连接测试
│   │       ├── datax_tasks.py       #     DataX 任务 CRUD + 触发 + 状态
│   │       ├── doris_query.py      #     SQL 执行 + 保存查询 + 历史
│   │       ├── dashboard.py        #     首页统计
│   │       └── system.py           #     系统配置 + 操作日志
│   ├── services/                   # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── role_service.py
│   │   ├── datasource_service.py
│   │   ├── datax_service.py        #   DataX 配置生成 + 任务管理
│   │   ├── spark_service.py        #   Spark 配置生成
│   │   ├── doris_service.py        #   Doris 查询执行
│   │   ├── component_service.py    #   组件配置加载 + 适配器初始化
│   │   ├── dashboard_service.py
│   │   └── system_service.py
│   ├── integrations/              # 组件适配层 (核心)
│   │   ├── base.py                #   ComponentAdapter 抽象基类
│   │   ├── airflow_client.py      #   Airflow REST API (DAG管理/触发/状态/日志)
│   │   ├── doris_client.py        #   Doris MySQL协议 (SQL查询/库表管理)
│   │   ├── cube_client.py         #   Cube REST API (指标查询) [未来]
│   │   ├── openmetadata_client.py #   OpenMetadata REST API (元数据/血缘) [未来]
│   │   ├── datax_config_gen.py    #   DataX job JSON 生成器 (不执行)
│   │   └── spark_config_gen.py     #   Spark 作业配置生成器 (不执行)
│   ├── models/                    # SQLAlchemy 数据模型
│   │   ├── base.py                #   Base 混合 (id, created_at, updated_at)
│   │   ├── user.py                #   User, Role, Permission, UserRole, RolePermission
│   │   ├── menu.py                #   Menu
│   │   ├── component.py           #   ComponentConfig
│   │   ├── datasource.py          #   DataSource
│   │   ├── datax_task.py          #   DataXTask, DataXFieldMapping
│   │   ├── task_instance.py       #   TaskInstance (Airflow DAG run 同步)
│   │   ├── doris_query.py         #   SavedQuery, QueryHistory
│   │   └── system.py              #   SystemConfig, OperationLog
│   ├── schemas/                   # Pydantic 请求/响应模型
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── datasource.py
│   │   ├── datax_task.py
│   │   ├── doris_query.py
│   │   └── ...
│   └── utils/
│       ├── crypto.py              #   加密工具
│       ├── pagination.py          #   分页工具
│       └── task_scheduler.py     #   APScheduler 定时轮询 Airflow 状态
├── alembic/                       # 数据库迁移
├── tests/
├── requirements.txt
├── .env.example
├── Dockerfile
└── alembic.ini
```

## 分层职责

| 层 | 职责 | 不做什么 |
|----|------|---------|
| API (api/v1) | 路由定义、参数校验、调用 Service | 不含业务逻辑 |
| Service (services) | 业务逻辑编排、调用 Integration | 不直接操作外部组件 |
| Integration (integrations) | 外部组件 API 适配、配置生成 | 不含业务判断 |
| Model (models) | 数据库 ORM 映射 | 不含业务逻辑 |
| Schema (schemas) | 请求/响应数据结构 | 不含逻辑 |

## 核心流程

### 数据同步流程 (DataX)
```
用户配置数据源+字段映射
  → datax_service 调用 datax_config_gen 生成 job JSON
  → 存入 datax_tasks.job_config (PostgreSQL)
  → datax_service 调用 airflow_client.trigger_dag_run('datax_sync', conf={task_id, job_json})
  → 创建 task_instance 记录
  → task_scheduler 定时轮询 airflow get_dag_run_state
  → 更新 task_instance.status
```

### 数据查询流程 (Doris)
```
用户输入 SQL
  → doris_service 调用 doris_client.execute_query(sql)
  → 返回结果 (columns + rows + row_count)
  → 记录到 query_history
```
