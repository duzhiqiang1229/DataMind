# DataMind 技术方案细化文档

## 一、工程结构总览

```
DataMind/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── core/              # 配置/数据库/Redis/安全/依赖
│   │   ├── api/v1/            # 10 个路由模块
│   │   ├── services/          # 业务逻辑层
│   │   ├── integrations/      # 组件适配层 (核心)
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   └── utils/            # 工具 (加密/分页/定时调度)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/             # Vue3 前端
│   ├── src/
│   │   ├── api/               # Axios + API 模块
│   │   ├── layouts/           # 主布局
│   │   ├── router/            # 路由 + 守卫
│   │   ├── stores/            # Pinia 状态管理
│   │   └── views/             # 6 个页面 (MVP)
│   ├── package.json
│   └── vite.config.ts
├── database/             # SQL 文件
│   ├── 001_init_schema.sql   # PostgreSQL 平台元数据 DDL
│   └── 002_doris_warehouse_init.sql  # Doris 数仓分层 + 模拟数据
└── airflow-dags/         # Airflow DAG 模板
    ├── datax_sync_dag.py     # DataX 同步 DAG
    ├── spark_job_dag.py      # Spark 加工 DAG (SQL + PySpark)
    └── README.md
```

## 二、后端分层架构

| 层 | 职责 | 关键文件 |
|----|------|---------|
| API | 路由/参数校验/调用Service | `app/api/v1/*.py` (10个路由) |
| Service | 业务编排/调用Integration | `app/services/*.py` |
| Integration | 外部组件适配 | `app/integrations/*.py` (6个适配器) |
| Model | ORM映射 | `app/models/*.py` |
| Schema | 请求/响应模型 | `app/schemas/*.py` |

### Integration Layer (核心)
```
integrations/
├── base.py              # ComponentAdapter 抽象基类
├── airflow_client.py    # Airflow REST API (DAG触发/状态/日志)
├── doris_client.py       # Doris MySQL协议 (SQL查询/库表浏览)
├── datax_config_gen.py   # DataX job JSON 生成器 (存库不执行)
├── spark_config_gen.py   # Spark 配置生成器 (SQL+PySpark, 存库不执行)
├── cube_client.py        # [未来] Cube REST API
└── openmetadata_client.py # [未来] OpenMetadata REST API
```

## 三、数据库设计 (PostgreSQL)

### 表清单 (16 张表)

| 分组 | 表名 | 用途 |
|------|------|------|
| RBAC | users | 用户 |
| RBAC | roles | 角色 |
| RBAC | permissions | 权限 |
| RBAC | user_roles | 用户-角色关联 |
| RBAC | role_permissions | 角色-权限关联 |
| RBAC | menus | 菜单(路由+按钮权限) |
| RBAC | role_menus | 角色-菜单关联 |
| 组件 | component_configs | 外部组件连接配置 |
| 数据源 | data_sources | 数据源配置 |
| DataX | datax_tasks | 同步任务定义(含job_config) |
| DataX | datax_field_mappings | 字段映射 |
| 执行 | task_instances | 任务执行实例(Airflow DAG Run映射) |
| 模型 | data_models | 数据模型(ODS/DWD/DWS/ADS) |
| 模型 | data_model_fields | 模型字段定义 |
| 模型 | data_model_versions | 模型版本历史 |
| 发布 | publish_tasks | 发布任务管理 |
| 发布 | publish_records | 发布记录 |
| 查询 | saved_queries | 保存的SQL |
| 查询 | query_history | 查询历史 |
| 系统 | system_configs | 系统配置 |
| 系统 | operation_logs | 操作日志 |

### 关键设计

- **component_configs**: `config_json`(非敏感) + `credentials_encrypted`(Fernet加密) 分离存储
- **datax_tasks.job_config**: JSONB 存储完整 DataX job JSON,触发时传给 Airflow
- **task_instances**: 映射 Airflow DAG Run,状态由定时轮询同步
- **data_models**: 按 ODS/DWD/DWS/ADS 分层管理数仓模型设计
- **data_model_versions**: 每次修改保存版本快照,支持回溯
- **publish_tasks**: 统一管理模型/任务的发布上线流程

## 四、API 接口清单

| 模块 | 路由前缀 | 关键接口 |
|------|---------|---------|
| 认证 | /api/v1/auth | login, refresh, me, logout |
| 用户 | /api/v1/users | CRUD + 重置密码 + 角色分配 |
| 角色 | /api/v1/roles | CRUD + 权限/菜单分配 |
| 菜单 | /api/v1/menus | 树形CRUD |
| 组件 | /api/v1/components | CRUD + 健康检查 |
| 数据源 | /api/v1/datasources | CRUD + 连接测试 + 表/字段查询 |
| DataX | /api/v1/datax-tasks | CRUD + 触发 + 暂停/恢复 + 执行历史 + 日志 |
| Spark | /api/v1/spark-tasks | CRUD + 触发 + 执行历史 + 日志 |
| 模型 | /api/v1/data-models | CRUD + 字段管理 + 版本管理 + DDL生成 |
| 发布 | /api/v1/publish | 发布任务 + 执行发布 + 发布记录 |
| 查询 | /api/v1/doris-query | 执行SQL + 库表浏览 + 保存查询 + 历史 |
| 首页 | /api/v1/dashboard | 统计 + 最近任务 + 组件状态 |
| 系统 | /api/v1/system | 配置管理 + 操作日志 |

## 五、Airflow DAG 模板

| DAG | 触发方式 | 参数 | 执行内容 |
|-----|---------|------|---------|
| datax_sync | DataMind REST API | task_id + job_json | datax.py 执行同步 |
| spark_job | DataMind REST API | task_id + spark_config | spark-sql / spark-submit |

### 执行链路
```
DataMind 配置任务 → 生成配置存入 PostgreSQL
  → Airflow REST API trigger_dag_run(dag_id, conf)
  → Airflow 执行 DAG task
  → DataMind 定时轮询(10秒) get_dag_run_state
  → 更新 task_instances.status
```

## 六、前端页面 (MVP)

| 页面 | 路由 | 组件 |
|------|------|------|
| 登录 | /login | 用户名密码 → JWT |
| 首页驾驶舱 | /dashboard | 4统计卡片 + 7天趋势图 + 最近任务 + 组件状态 |
| 数据源管理 | /datasource | 表格 + CRUD + 连接测试 |
| DataX 同步 | /datax | 任务列表 + 触发执行 + 历史记录 |
| SQL 工作台 | /query | 库表树 + SQL编辑器 + 结果表格 |
| 用户管理 | /system/user | 用户CRUD + 角色分配 |

## 七、Doris 数仓分层 (MVP 模拟数据)

| 层 | 库 | 表 | 数据 |
|----|----|----|------|
| ODS | ods | ods_user, ods_order, ods_product | 3+4+3 条模拟数据 |
| DWD | dwd | dwd_user_fact, dwd_order_detail | (待 Spark 加工) |
| DWS | dws | dws_user_daily, dws_order_daily | (待 Spark 聚合) |
| ADS | ads | ads_dashboard_summary | (待 Spark 汇总) |
