# DataMind 系统架构设计文档

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：更新为 API 连接模式架构，明确 DataMind 不部署底层组件，Airflow 作为统一执行引擎

---

## 1. 文档概述

本文档描述 DataMind 企业智能平台的整体系统架构、技术架构、服务划分、组件交互、部署架构以及未来 AI 智能分析扩展方案。

**建设目标**：打造集数据集成、数据开发、数据仓库、指标管理、数据治理、数据服务和 AI 分析于一体的企业级数据平台。

**核心架构原则**：DataMind 不负责部署底层组件，通过 API 连接已部署的外部组件。

## 2. 总体架构设计

DataMind 企业智能平台采用分层架构设计：

| 层级 | 说明 | 部署方 |
|------|------|--------|
| 数据源层 | 企业业务系统产生的数据 | 外部 |
| 数据集成层 | DataX 负责数据采集同步（通过 Airflow 执行） | 外部已部署 |
| 数据计算层 | Spark 负责数据加工处理（通过 Airflow 执行） | 外部已部署 |
| 数据仓库层 | Doris 负责统一分析存储 | 外部已部署 |
| 语义指标层 | Cube 负责指标定义和查询服务 | 外部已部署 |
| 数据治理层 | OpenMetadata 负责元数据、血缘和质量管理 | 外部已部署 |
| 应用服务层 | DataMind 提供统一门户、API 编排和 AI Agent 能力 | DataMind 自部署 |

## 3. 技术架构

### DataMind 自部署技术栈

| 技术 | 用途 |
|------|------|
| Vue 3.5 + TypeScript | 前端门户 |
| Element Plus + ECharts | 前端 UI 组件 |
| Python 3.12 + FastAPI | 后端服务 |
| SQLAlchemy 2.x | 数据访问 |
| PostgreSQL 16 | 业务数据库 |
| Redis 7.2 | 缓存 |
| APScheduler | Airflow 状态轮询 |

### 外部组件技术栈（已独立部署）

| 技术 | 用途 | 集成方式 |
|------|------|---------|
| DataX 3.0 | 数据同步 | Airflow DAG 执行 CLI |
| Spark 3.5.3 | 数据加工 | Airflow DAG 提交 spark-submit |
| Airflow 2.10 | 任务调度 | REST API 直连 |
| Doris 3.0 | 数据仓库 | MySQL 协议直连 |
| Cube 1.3 | 指标语义 | REST API 直连 |
| OpenMetadata 1.8 | 数据治理 | REST API 直连 |

## 4. 系统分层架构

```
┌─────────────────────────────────────────┐
│         用户访问层                       │
│  企业数据门户 / BI / AI 助手              │
├─────────────────────────────────────────┤
│         业务服务层（DataMind 后端）        │
│  权限管理 / 任务管理 / 指标管理 / 数据服务 │
│  ┌─────────────────────────────────┐    │
│  │     Integration Layer           │    │
│  │  4 适配器 + 2 配置生成器          │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│         外部数据能力层（已独立部署）        │
│  DataX / Spark / Airflow / Doris /      │
│  Cube / OpenMetadata                    │
├─────────────────────────────────────────┤
│         数据源层                         │
│  ERP / CRM / OA / 业务数据库 / 文件 / 接口 │
└─────────────────────────────────────────┘
```

## 5. 前端架构设计

采用 Vue 3 单页面应用架构，从零自建。

主要模块：
- 首页数据驾驶舱
- 数据源管理
- 数据集成管理（DataX）
- 数据开发管理（Spark）
- 调度任务管理（Airflow）
- 数据仓库浏览（Doris）
- 数据资产管理（OpenMetadata）
- 指标中心（Cube）
- 数据服务中心
- 系统管理

通过 HTTP API 与后端服务通信，Axios 拦截器统一注入 JWT Token。

## 6. 后端服务架构设计

采用模块化服务设计。

核心模块：

| 序号 | 模块 | 说明 |
|------|------|------|
| 1 | 用户权限服务 | RBAC + JWT 认证 |
| 2 | 数据源管理服务 | 数据源 CRUD + 连接测试 |
| 3 | DataX 任务管理服务 | 生成 job JSON + Airflow 触发 |
| 4 | Airflow 调度管理服务 | DAG 模板管理 + 状态轮询 |
| 5 | Spark 任务管理服务 | SQL/PySpark 配置 + Airflow 触发 |
| 6 | Cube 指标服务 | REST API 集成 |
| 7 | OpenMetadata 治理服务 | REST API 集成 |
| 8 | 数据查询服务 | Doris MySQL 协议查询 |

后端负责业务编排，不替代底层开源组件。

## 7. Integration Layer 设计

Integration Layer 是 DataMind 后端的核心层，负责与外部组件交互。

### 4 个 API 适配器

| 适配器 | 连接方式 | 能力 |
|--------|---------|------|
| `airflow_client.py` | REST API | DAG 列表、触发执行、状态查询、日志获取 |
| `doris_client.py` | MySQL 协议 | SQL 查询、库表管理、元数据获取 |
| `cube_client.py` | REST API | 指标查询、模型元数据 |
| `openmetadata_client.py` | REST API | 数据目录、血缘、质量 |

### 2 个配置生成器

| 生成器 | 说明 |
|--------|------|
| `datax_config_gen.py` | 根据用户配置生成 DataX job JSON，存入 PostgreSQL，不直接执行 |
| `spark_config_gen.py` | 生成 Spark 作业配置，管理 SQL 文件和 PySpark 脚本，存入 PostgreSQL，不直接执行 |

### 组件连接配置

组件连接信息存储在 PostgreSQL `component_configs` 表：

```sql
CREATE TABLE component_configs (
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(50) NOT NULL,
    config_json JSONB NOT NULL,        -- base_url, port 等
    credentials_encrypted TEXT,        -- 加密的认证信息
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

DataMind 启动时从表中加载配置，动态初始化适配器。通过系统管理 UI 可视化管理。

## 8. 核心组件交互设计

### 数据同步流程

```
用户配置数据源/表/字段映射
        ↓
DataMind 生成 DataX job JSON（存库）
        ↓
DataMind 调用 Airflow REST API 触发 DAG（传 job_json 参数）
        ↓
Airflow DAG 模板执行 datax.py
        ↓
DataMind 轮询 Airflow API 获取状态（约 10 秒）
        ↓
更新状态到本地库，用户界面展示
```

### 数据加工流程

```
用户编写 SQL / PySpark 脚本
        ↓
DataMind 存储 SQL/脚本文件 + 提交参数到 PostgreSQL
        ↓
DataMind 调用 Airflow REST API 触发 DAG（传配置参数）
        ↓
Airflow DAG 模板执行 spark-sql / spark-submit
        ↓
DataMind 轮询 Airflow API 获取状态
        ↓
更新状态到本地库，用户界面展示
```

### 指标查询流程

```
用户请求指标
    ↓
DataMind → Cube REST API → Doris → 返回指标结果
```

### 治理流程

```
DataMind → OpenMetadata REST API → 返回元数据/血缘/质量信息
```

## 9. 数据流程架构

完整数据链路：

```
业务系统
    ↓
DataX 数据采集（Airflow 执行）
    ↓
Doris 数据仓库（ODS → DWD → DWS → ADS）
    ↓
Spark 数据加工（Airflow 执行）
    ↓
Cube 指标服务
    ↓
BI / 数据 API / AI Agent
```

## 10. 权限架构设计

采用 RBAC 权限模型。

角色：
- 系统管理员
- 数据工程师
- 数据分析师
- 业务用户
- 数据治理人员

控制范围：菜单权限、数据权限、接口权限、操作审计。

认证流程：登录 → 验证账号 → 生成 JWT Token → 访问接口。

## 11. 部署架构设计

### DataMind 自身部署（4 个服务）

| 服务 | 容器 | 说明 |
|------|------|------|
| Vue 前端 | frontend | Nginx 发布静态资源 |
| FastAPI 后端 | backend | uvicorn 运行 |
| PostgreSQL | postgres | 平台元数据 |
| Redis | redis | 缓存 |

### 外部组件（已独立部署）

Doris、Airflow、Spark、Cube、OpenMetadata 已独立部署在各自环境中，DataMind 通过网络连接其 API。

### 开发环境

使用 Docker Compose 部署 DataMind 4 个服务。外部组件连接开发环境已有的实例。

### 生产环境

推荐 Kubernetes 部署 DataMind 4 个服务。外部组件保持各自独立部署。

## 12. 任务状态同步设计

DataMind 采用**定时轮询**方式同步 Airflow 任务状态：

- 后端使用 APScheduler 定时任务
- 默认每 10 秒轮询一次 Airflow REST API
- 查询正在运行的 DAG Run 状态
- 更新到本地 `task_instances` 表
- 用户界面实时展示任务执行状态

## 13. AI 智能分析扩展架构

未来增加企业语义层和 AI Agent。

流程：

```
用户自然语言问题
    ↓
AI Agent 理解业务意图
    ↓
企业语义层匹配业务知识
    ↓
Cube 生成指标查询
    ↓
Doris 返回数据
    ↓
AI 生成分析结论
```

## 14. 系统演进路线

| 阶段 | 内容 | 目标 |
|------|------|------|
| 第一阶段 | MVP 核心链路 | 登录 + 数据源 + DataX + Doris 查询 + 系统管理 |
| 第二阶段 | 数据开发与调度 | Spark + Airflow + Cube 指标 |
| 第三阶段 | 数据治理 | OpenMetadata 集成 |
| 第四阶段 | 智能分析 | 企业语义层 + AI Agent |

## 15. 总结

DataMind 企业智能平台通过 API 连接 DataX、Spark、Airflow、Doris、Cube、OpenMetadata 六大已部署组件，形成现代化数据平台架构。

DataMind 自身只需部署 4 个服务（Vue + FastAPI + PostgreSQL + Redis），专注做统一门户、配置管理、流程编排和 UI/UX 层，大幅降低运维负担。
