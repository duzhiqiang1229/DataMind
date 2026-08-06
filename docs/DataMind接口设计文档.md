# DataMind 企业智能平台接口设计文档

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：细化接口路径和请求/响应模型，补充组件连接配置接口，明确 Airflow DAG 触发参数

---

## 1. 文档概述

本文档定义 DataMind 企业智能平台前后端接口规范，以及中台与 Airflow、Doris、Cube、OpenMetadata 等组件之间的接口交互方式。

**接口设计目标**：统一服务入口、降低组件耦合、支撑数据开发、治理、服务和 AI 应用。

## 2. 接口架构设计

```
前端 Vue 门户
    ↓ HTTP/JSON
FastAPI 业务服务层
    ↓ Integration Layer
外部组件 API（Airflow REST / Doris MySQL / Cube REST / OpenMetadata REST）
```

FastAPI 负责业务编排，不直接替代底层组件能力。

## 3. 接口规范

| 项目 | 规范 |
|------|------|
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |
| 认证方式 | JWT Token（Bearer） |
| 接口风格 | RESTful API |
| API 前缀 | `/api/v1` |

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

## 4. 用户权限接口

### 4.1 用户登录

```
POST /api/v1/auth/login
```

请求：
```json
{
  "username": "admin",
  "password": "xxx"
}
```

返回：
```json
{
  "code": 200,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "real_name": "管理员",
      "roles": ["admin"]
    }
  }
}
```

### 4.2 获取当前用户信息

```
GET /api/v1/auth/me
```

### 4.3 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/users` | 用户列表（分页） |
| POST | `/api/v1/users` | 创建用户 |
| GET | `/api/v1/users/{id}` | 用户详情 |
| PUT | `/api/v1/users/{id}` | 更新用户 |
| DELETE | `/api/v1/users/{id}` | 删除用户 |
| PUT | `/api/v1/users/{id}/roles` | 分配角色 |
| PUT | `/api/v1/users/{id}/password` | 修改密码 |

### 4.4 角色管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/roles` | 角色列表 |
| POST | `/api/v1/roles` | 创建角色 |
| PUT | `/api/v1/roles/{id}` | 更新角色 |
| DELETE | `/api/v1/roles/{id}` | 删除角色 |
| PUT | `/api/v1/roles/{id}/permissions` | 分配权限 |

### 4.5 菜单管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/menus` | 菜单树 |
| POST | `/api/v1/menus` | 创建菜单 |
| PUT | `/api/v1/menus/{id}` | 更新菜单 |
| DELETE | `/api/v1/menus/{id}` | 删除菜单 |

## 5. 组件连接配置接口

> 管理 6 大外部组件的连接信息

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/components` | 组件列表 |
| GET | `/api/v1/components/{name}` | 组件详情 |
| PUT | `/api/v1/components/{name}` | 更新组件配置 |
| POST | `/api/v1/components/{name}/test` | 测试组件连接 |

请求（更新配置）：
```json
{
  "config": {
    "base_url": "http://airflow-host:8080",
    "port": 8080
  },
  "credentials": {
    "auth_type": "token",
    "token": "xxx"
  }
}
```

> 注：credentials 使用 Fernet 加密存储。

## 6. 数据源管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/datasources` | 数据源列表（分页） |
| POST | `/api/v1/datasources` | 创建数据源 |
| GET | `/api/v1/datasources/{id}` | 数据源详情 |
| PUT | `/api/v1/datasources/{id}` | 更新数据源 |
| DELETE | `/api/v1/datasources/{id}` | 删除数据源 |
| POST | `/api/v1/datasources/test` | 测试连接 |
| GET | `/api/v1/datasources/{id}/tables` | 获取数据源表列表 |
| GET | `/api/v1/datasources/{id}/tables/{table}/columns` | 获取表字段 |

请求（创建数据源）：
```json
{
  "name": "业务数据库",
  "type": "mysql",
  "host": "192.168.1.100",
  "port": 3306,
  "database_name": "business",
  "username": "reader",
  "password": "xxx"
}
```

## 7. DataX 数据同步接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/datax/tasks` | 同步任务列表（分页） |
| POST | `/api/v1/datax/tasks` | 创建同步任务 |
| GET | `/api/v1/datax/tasks/{id}` | 任务详情 |
| PUT | `/api/v1/datax/tasks/{id}` | 更新任务 |
| DELETE | `/api/v1/datax/tasks/{id}` | 删除任务 |
| POST | `/api/v1/datax/tasks/{id}/run` | 触发执行（调用 Airflow API） |
| POST | `/api/v1/datax/tasks/{id}/pause` | 暂停任务 |
| POST | `/api/v1/datax/tasks/{id}/resume` | 恢复任务 |
| GET | `/api/v1/datax/tasks/{id}/instances` | 执行历史 |
| GET | `/api/v1/datax/tasks/{id}/instances/{run_id}/logs` | 执行日志 |

请求（创建同步任务）：
```json
{
  "task_name": "Oracle业务表同步",
  "source_id": 1,
  "target_database": "ods",
  "target_table": "ods_business_orders",
  "sync_mode": "full",
  "schedule_cron": "0 2 * * *",
  "field_mappings": [
    {"source_column": "ORDER_ID", "target_column": "order_id", "data_type": "BIGINT"},
    {"source_column": "ORDER_AMOUNT", "target_column": "order_amount", "data_type": "DECIMAL(18,2)"}
  ]
}
```

> DataMind 后端根据配置自动生成 DataX job JSON 存库，触发时传给 Airflow DAG。

## 8. Spark 任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/spark/tasks` | 任务列表（分页） |
| POST | `/api/v1/spark/tasks` | 创建 Spark 任务 |
| GET | `/api/v1/spark/tasks/{id}` | 任务详情 |
| PUT | `/api/v1/spark/tasks/{id}` | 更新任务 |
| DELETE | `/api/v1/spark/tasks/{id}` | 删除任务 |
| POST | `/api/v1/spark/tasks/{id}/run` | 触发执行（调用 Airflow API） |
| GET | `/api/v1/spark/tasks/{id}/instances` | 执行历史 |
| GET | `/api/v1/spark/tasks/{id}/instances/{run_id}/logs` | 执行日志 |

请求（创建 Spark 任务）：
```json
{
  "task_name": "DWD订单明细加工",
  "task_type": "sql",
  "sql_content": "INSERT INTO dwd.dwd_order_detail SELECT ...",
  "submit_params": {
    "driver_memory": "2g",
    "executor_memory": "4g",
    "num_executors": 4
  },
  "schedule_cron": "0 3 * * *"
}
```

> task_type 支持 `sql` 和 `pyspark`。pyspark 模式使用 `script_content` 代替 `sql_content`。

## 8.5 数据模型管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/data-models` | 模型列表（支持按层级 ODS/DWD/DWS/ADS 筛选） |
| POST | `/api/v1/data-models` | 创建数据模型 |
| GET | `/api/v1/data-models/{id}` | 模型详情 |
| PUT | `/api/v1/data-models/{id}` | 更新模型 |
| DELETE | `/api/v1/data-models/{id}` | 删除模型 |
| GET | `/api/v1/data-models/{id}/fields` | 模型字段列表 |
| POST | `/api/v1/data-models/{id}/fields` | 添加字段 |
| PUT | `/api/v1/data-models/{id}/fields/{field_id}` | 更新字段 |
| DELETE | `/api/v1/data-models/{id}/fields/{field_id}` | 删除字段 |
| GET | `/api/v1/data-models/{id}/versions` | 模型版本列表 |
| POST | `/api/v1/data-models/{id}/versions` | 保存新版本 |
| GET | `/api/v1/data-models/{id}/sql` | 模型建表 SQL |

请求（创建数据模型）：
```json
{
  "model_name": "dwd_order_detail",
  "model_code": "dwd_order_detail",
  "layer": "dwd",
  "database": "dwd",
  "table_name": "dwd_order_detail",
  "description": "订单明细明细表"
}
```

> layer 支持 `ods`、`dwd`、`dws`、`ads`。模型通过版本管理支持迭代开发。

## 8.6 发布管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/publish/tasks` | 发布任务列表 |
| POST | `/api/v1/publish/tasks` | 创建发布任务 |
| GET | `/api/v1/publish/tasks/{id}` | 发布任务详情 |
| POST | `/api/v1/publish/tasks/{id}/execute` | 执行发布 |
| GET | `/api/v1/publish/tasks/{id}/records` | 发布记录 |
| GET | `/api/v1/publish/records/{id}` | 发布结果详情 |

请求（创建发布任务）：
```json
{
  "publish_name": "DWD层订单模型发布",
  "publish_type": "model",
  "source_ids": [1, 2, 3],
  "target_environment": "production",
  "description": "发布 DWD 订单明细模型到生产环境"
}
```

> publish_type 支持 `model`（数据模型）、`spark_task`（Spark 任务）、`datax_task`（DataX 任务）。

## 9. Airflow 调度接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/airflow/dags` | DAG 列表（从 Airflow API 获取） |
| GET | `/api/v1/airflow/dags/{dag_id}` | DAG 详情 |
| POST | `/api/v1/airflow/dags/{dag_id}/dagRuns` | 触发 DAG 执行 |
| GET | `/api/v1/airflow/dags/{dag_id}/dagRuns` | DAG Run 列表 |
| GET | `/api/v1/airflow/dags/{dag_id}/dagRuns/{run_id}` | DAG Run 状态 |
| GET | `/api/v1/airflow/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs` | 获取日志 |

> Airflow DAG 使用预置模板 + 参数触发模式。

## 10. Doris 数据查询接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/doris/databases` | 数据库列表 |
| GET | `/api/v1/doris/databases/{db}/tables` | 表列表 |
| GET | `/api/v1/doris/databases/{db}/tables/{table}/columns` | 表字段 |
| POST | `/api/v1/doris/query` | 执行 SQL 查询 |
| GET | `/api/v1/doris/queries/saved` | 保存的查询列表 |
| POST | `/api/v1/doris/queries/saved` | 保存查询 |
| GET | `/api/v1/doris/queries/history` | 查询历史 |

请求（SQL 查询）：
```json
{
  "sql": "SELECT * FROM ods.ods_business_orders LIMIT 100",
  "database": "ods",
  "limit": 100
}
```

返回：
```json
{
  "code": 200,
  "data": {
    "columns": ["order_id", "order_amount", "create_time"],
    "rows": [["1001", 299.00, "2026-01-01"]],
    "total": 1,
    "duration_ms": 150
  }
}
```

## 11. Cube 指标服务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/metrics` | 指标列表 |
| GET | `/api/v1/metrics/{code}` | 指标详情 |
| POST | `/api/v1/metrics/query` | 查询指标数据（调用 Cube API） |
| GET | `/api/v1/cube/models` | Cube 模型元数据 |

请求（查询指标）：
```json
{
  "metric_code": "sales_amount",
  "dimensions": ["month"],
  "filters": {"month": "2026-01"},
  "time_dimensions": {
    "granularity": "month",
    "date_range": ["2026-01-01", "2026-06-30"]
  }
}
```

## 12. OpenMetadata 治理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/metadata/tables` | 数据表目录 |
| GET | `/api/v1/metadata/tables/{id}` | 表详情 |
| GET | `/api/v1/metadata/lineage/{table_id}` | 血缘关系 |
| GET | `/api/v1/metadata/quality/{table_id}` | 数据质量 |
| POST | `/api/v1/metadata/sync` | 触发元数据同步 |

## 13. 首页看板接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboard/stats` | 统计卡片数据 |
| GET | `/api/v1/dashboard/task-trend` | 任务趋势图 |
| GET | `/api/v1/dashboard/component-status` | 组件连接状态 |

## 14. 系统管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/system/configs` | 系统配置列表 |
| PUT | `/api/v1/system/configs/{key}` | 更新配置 |
| GET | `/api/v1/system/logs` | 操作日志列表（分页） |

## 15. 接口安全设计

安全措施：
1. JWT 身份认证
2. RBAC 权限控制
3. 数据权限控制
4. API 访问日志
5. 参数校验（Pydantic）
6. 组件凭证 Fernet 加密存储

## 16. 接口异常规范

错误码：

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 参数校验失败 |
| 502 | 组件调用异常 |
| 500 | 服务异常 |

所有异常返回统一 JSON 格式。

## 17. 接口演进规划

| 阶段 | 接口 |
|------|------|
| 第一阶段 | 基础管理接口（认证 + 用户 + 数据源 + DataX + Doris 查询 + 组件配置） |
| 第二阶段 | 数据开发接口（Spark + Airflow） |
| 第三阶段 | 指标语义接口（Cube） |
| 第四阶段 | AI Agent 智能接口 |
