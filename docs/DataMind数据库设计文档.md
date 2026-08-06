# DataMind 企业智能平台数据库设计文档

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：更新表名规范为 snake_case，补充 component_configs 组件配置表，细化 DataX/Spark 任务配置存储

---

## 1. 文档概述

本文档用于定义 DataMind 企业智能平台业务数据库设计，包括用户权限、数据源管理、任务管理、指标管理、数据服务管理以及系统审计等核心业务表结构。

**说明**：Doris 负责业务分析数据存储，本数据库（PostgreSQL）主要用于保存中台自身业务配置和管理信息。

## 2. 数据库选型

| 项目 | 技术 | 用途 |
|------|------|------|
| 数据库 | PostgreSQL 16 | 存储 DataMind 平台系统元数据、配置数据、权限信息和业务管理数据 |
| 缓存 | Redis 7.2 | 任务状态缓存、接口缓存和系统性能优化 |

## 3. 数据库总体模型

数据库主要划分为以下模块：

| 序号 | 模块 | 表数量 |
|------|------|--------|
| 1 | 用户权限模块 | 7 张表 |
| 2 | 组件配置模块 | 1 张表 |
| 3 | 数据源管理模块 | 1 张表 |
| 4 | DataX 任务模块 | 2 张表 |
| 5 | Spark 任务模块 | 1 张表 |
| 6 | 执行实例模块 | 1 张表 |
| 7 | 数据查询模块 | 2 张表 |
| 8 | 系统管理模块 | 2 张表 |

## 4. 用户权限设计（RBAC）

### 用户表 `sys_users`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| username | VARCHAR(50) | 用户名（唯一） |
| password_hash | VARCHAR(255) | 密码哈希 |
| real_name | VARCHAR(50) | 姓名 |
| email | VARCHAR(100) | 邮箱 |
| phone | VARCHAR(20) | 手机号 |
| status | VARCHAR(20) | 状态（active/inactive） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 角色表 `sys_roles`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| role_name | VARCHAR(50) | 角色名称 |
| role_code | VARCHAR(50) | 角色编码（唯一） |
| description | TEXT | 描述 |
| status | VARCHAR(20) | 状态 |
| created_at | TIMESTAMP | 创建时间 |

### 权限表 `sys_permissions`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| permission_name | VARCHAR(50) | 权限名称 |
| permission_code | VARCHAR(50) | 权限编码（唯一） |
| type | VARCHAR(20) | 类型（menu/button/api） |
| parent_id | BIGINT | 父权限 ID |
| path | VARCHAR(255) | 路由路径 |
| created_at | TIMESTAMP | 创建时间 |

### 菜单表 `sys_menus`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| parent_id | BIGINT | 父菜单 ID |
| menu_name | VARCHAR(50) | 菜单名称 |
| path | VARCHAR(255) | 路由路径 |
| component | VARCHAR(255) | 组件路径 |
| icon | VARCHAR(50) | 图标 |
| sort_order | INT | 排序 |
| visible | BOOLEAN | 是否可见 |
| created_at | TIMESTAMP | 创建时间 |

### 用户角色关系表 `sys_user_roles`

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | BIGINT | 用户 ID |
| role_id | BIGINT | 角色 ID |

> 主键：(user_id, role_id)

### 角色权限关系表 `sys_role_permissions`

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | BIGINT | 角色 ID |
| permission_id | BIGINT | 权限 ID |

> 主键：(role_id, permission_id)

### 角色菜单关系表 `sys_role_menus`

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | BIGINT | 角色 ID |
| menu_id | BIGINT | 菜单 ID |

> 主键：(role_id, menu_id)

## 5. 组件配置模块

### 组件配置表 `component_configs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| component_name | VARCHAR(50) | 组件名称（airflow/doris/cube/openmetadata） |
| config_json | JSONB | 配置（base_url, port 等） |
| credentials_encrypted | TEXT | 加密的认证信息（Fernet） |
| status | VARCHAR(20) | 状态（active/inactive） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

> 管理 6 大外部组件的连接信息。DataMind 启动时从表中加载配置，动态初始化适配器。

## 6. 数据源管理模块

### 数据源表 `data_sources`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| name | VARCHAR(100) | 数据源名称 |
| type | VARCHAR(20) | 类型（oracle/mysql/postgresql） |
| host | VARCHAR(255) | 地址 |
| port | INT | 端口 |
| database_name | VARCHAR(100) | 数据库名 |
| username | VARCHAR(100) | 用户名 |
| password_encrypted | TEXT | 加密密码 |
| status | VARCHAR(20) | 状态 |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

用于管理 Oracle、MySQL、PostgreSQL 等企业数据源。

## 7. DataX 数据同步任务设计

### 同步任务表 `datax_tasks`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| task_name | VARCHAR(100) | 任务名称 |
| source_id | BIGINT | 来源数据源 ID |
| target_database | VARCHAR(50) | 目标库（Doris） |
| target_table | VARCHAR(100) | 目标表 |
| sync_mode | VARCHAR(20) | 同步类型（full/incremental） |
| schedule_cron | VARCHAR(50) | 调度表达式 |
| job_config | JSONB | DataX job JSON 配置 |
| status | VARCHAR(20) | 状态（active/paused） |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 字段映射表 `datax_field_mappings`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| task_id | BIGINT | 任务 ID |
| source_column | VARCHAR(100) | 源字段 |
| target_column | VARCHAR(100) | 目标字段 |
| data_type | VARCHAR(50) | 数据类型 |
| is_primary_key | BOOLEAN | 是否主键 |
| created_at | TIMESTAMP | 创建时间 |

## 8. Spark 数据开发任务设计

### Spark 任务表 `spark_tasks`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| task_name | VARCHAR(100) | 任务名称 |
| task_type | VARCHAR(20) | 类型（sql/pyspark） |
| sql_content | TEXT | SQL 内容（sql 模式） |
| script_content | TEXT | PySpark 脚本内容（pyspark 模式） |
| submit_params | JSONB | 提交参数（driver_memory, executor_memory 等） |
| target_database | VARCHAR(50) | 目标库 |
| target_table | VARCHAR(100) | 目标表 |
| schedule_cron | VARCHAR(50) | 调度表达式 |
| status | VARCHAR(20) | 状态 |
| version | INT | 版本号 |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

用于管理 SQL 任务和 PySpark 脚本任务。

## 8.5 数据模型管理设计

### 数据模型表 `data_models`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| model_name | VARCHAR(100) | 模型名称 |
| model_code | VARCHAR(100) | 模型编码（唯一） |
| layer | VARCHAR(20) | 数仓分层（ods/dwd/dws/ads） |
| database | VARCHAR(50) | Doris 数据库名 |
| table_name | VARCHAR(100) | Doris 表名 |
| description | TEXT | 模型描述 |
| status | VARCHAR(20) | 状态（draft/published/archived） |
| current_version | INT | 当前版本号 |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 数据模型字段表 `data_model_fields`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| model_id | BIGINT | 关联模型 ID |
| field_name | VARCHAR(100) | 字段名称 |
| field_type | VARCHAR(50) | 字段类型 |
| field_comment | VARCHAR(200) | 字段注释 |
| is_primary_key | BOOLEAN | 是否主键 |
| is_partition | BOOLEAN | 是否分区字段 |
| default_value | VARCHAR(100) | 默认值 |
| sort_order | INT | 排序序号 |

### 数据模型版本表 `data_model_versions`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| model_id | BIGINT | 关联模型 ID |
| version | INT | 版本号 |
| table_ddl | TEXT | 建表 SQL |
| field_snapshot | JSONB | 字段快照（JSON） |
| change_log | TEXT | 变更说明 |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |

## 8.6 发布管理设计

### 发布任务表 `publish_tasks`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| publish_name | VARCHAR(100) | 发布名称 |
| publish_type | VARCHAR(20) | 类型（model/spark_task/datax_task） |
| source_ids | JSONB | 发布对象 ID 列表 |
| target_environment | VARCHAR(20) | 目标环境（dev/staging/production） |
| description | TEXT | 发布说明 |
| status | VARCHAR(20) | 状态（pending/executing/success/failed） |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |
| executed_at | TIMESTAMP | 执行时间 |

### 发布记录表 `publish_records`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| publish_task_id | BIGINT | 关联发布任务 ID |
| source_id | BIGINT | 发布对象 ID |
| source_type | VARCHAR(20) | 对象类型 |
| source_name | VARCHAR(100) | 对象名称 |
| result | VARCHAR(20) | 发布结果（success/failed） |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 记录时间 |

## 9. 执行实例设计

### 任务实例表 `task_instances`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| task_id | BIGINT | 任务 ID |
| task_type | VARCHAR(20) | 任务类型（datax/spark） |
| dag_run_id | VARCHAR(255) | Airflow DAG Run ID |
| status | VARCHAR(20) | 执行状态（pending/running/success/failed） |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| duration_seconds | INT | 执行时长（秒） |
| read_count | BIGINT | 读取记录数 |
| write_count | BIGINT | 写入记录数 |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

映射 Airflow DAG Run，记录同步统计信息。状态通过轮询 Airflow API 更新。

## 10. 数据查询模块

### 保存查询表 `saved_queries`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| query_name | VARCHAR(100) | 查询名称 |
| database | VARCHAR(50) | 数据库 |
| sql_content | TEXT | SQL 内容 |
| description | TEXT | 描述 |
| created_by | BIGINT | 创建人 |
| created_at | TIMESTAMP | 创建时间 |

### 查询历史表 `query_history`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| sql_content | TEXT | SQL 内容 |
| database | VARCHAR(50) | 数据库 |
| duration_ms | INT | 执行时长（毫秒） |
| row_count | INT | 返回行数 |
| status | VARCHAR(20) | 状态（success/failed） |
| error_message | TEXT | 错误信息 |
| created_by | BIGINT | 用户 ID |
| created_at | TIMESTAMP | 创建时间 |

## 11. 系统管理模块

### 系统配置表 `system_configs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| config_key | VARCHAR(100) | 配置键（唯一） |
| config_value | TEXT | 配置值 |
| config_type | VARCHAR(20) | 类型（string/number/boolean/json） |
| description | TEXT | 描述 |
| updated_at | TIMESTAMP | 更新时间 |

### 操作日志表 `operation_logs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| user_id | BIGINT | 用户 ID |
| username | VARCHAR(50) | 用户名 |
| operation_type | VARCHAR(50) | 操作类型 |
| operation_content | TEXT | 操作内容 |
| ip_address | VARCHAR(50) | IP 地址 |
| created_at | TIMESTAMP | 创建时间 |

用于系统审计和问题追踪。

## 12. 表关系设计

核心关系：

```
用户 → 角色 → 权限
用户 → 角色 → 菜单
数据源 → DataX 任务 → 字段映射
DataX 任务 → 任务实例
Spark 任务 → 任务实例
组件配置 → Integration Layer 适配器
```

## 13. 数据库设计原则

1. 中台业务库与分析库分离（PostgreSQL 管理配置，Doris 承载分析数据）
2. 所有核心操作记录审计日志
3. JSON 配置使用 JSONB 类型
4. 敏感信息（密码、凭证）使用 Fernet 加密存储
5. 时间字段统一使用 `created_at` / `updated_at`
6. 支持未来微服务拆分和扩展

## 14. Doris 数仓设计（外部库）

> Doris 数仓表结构详见 `database/002_doris_warehouse_init.sql`

分层结构：
- **ODS 层**：原始数据（业务系统同步表）
- **DWD 层**：明细数据（清洗加工后）
- **DWS 层**：主题汇总（轻度聚合）
- **ADS 层**：应用数据（高度聚合，面向业务）

先建分层结构，使用模拟数据验证链路。

## 15. 后续扩展

未来增加企业语义层后，可增加：

| 表名 | 用途 |
|------|------|
| business_objects | 业务对象表 |
| business_relations | 业务关系表 |
| business_rules | 业务规则表 |
| knowledge_entities | 知识实体表 |

用于支撑 AI Agent 智能问数。
