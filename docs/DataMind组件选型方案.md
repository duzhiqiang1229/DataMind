# DataMind 企业智能平台组件选型方案

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：更新组件集成方式为 API 连接，明确各组件 API 类型和集成难度

---

## 1. 项目背景

建设统一的数据智能中台，实现数据采集、数据加工、数据仓库、指标管理、数据治理和 AI 智能分析能力。

**核心原则**：6 大数据组件已独立部署，DataMind 通过 API 连接使用，不负责部署运维。

## 2. 总体技术架构

```
数据源 → DataX 数据同步 → Doris 数据仓库 → Cube 指标语义层 → 数据服务/BI/AI Agent
                                    ↑
                            Spark 数据加工
                                    
Airflow 负责任务编排（DataX 和 Spark 均通过 Airflow 执行）
OpenMetadata 负责数据治理
```

**DataMind 定位**：统一控制层，通过 API 连接上述组件，自身只部署 Vue + FastAPI + PostgreSQL + Redis。

## 3. 核心组件选型

| 组件 | 版本 | 定位 | API 类型 | 集成难度 |
|------|------|------|---------|---------|
| DataX | 3.0 | 数据同步 | 无原生 API，通过 Airflow 执行 CLI | 中 |
| Spark | 3.5.3 | 数据加工计算 | 无原生 API，通过 Airflow 提交 | 中 |
| Airflow | 2.10.x | 任务调度编排 | REST API（完善） | 低 |
| Doris | 3.0.x | 数据仓库 OLAP | MySQL 协议 + HTTP API | 低 |
| Cube | 1.3.x | 指标语义层 | REST API（完善） | 低 |
| OpenMetadata | 1.8.x | 元数据治理 | REST API（完善） | 低 |

## 4. DataX 选型说明

- **定位**：企业数据集成平台
- **职责**：Oracle、MySQL 等业务系统与 Doris 之间的数据同步
- **优势**：插件丰富、稳定成熟、易于二次开发
- **集成方式**：DataMind 生成 DataX job JSON 存库 → Airflow DAG 模板执行 datax.py CLI
- **注意**：DataX 无原生 REST API，是命令行工具，通过 Airflow 统一执行

## 5. Spark 选型说明

- **定位**：分布式数据计算引擎
- **职责**：ODS 到 DWD、DWS、ADS 的数据加工任务
- **推荐环境**：Java 17、Scala 2.12、Python 3.12
- **集成方式**：DataMind 生成 SQL/PySpark 配置存库 → Airflow DAG 模板执行 spark-sql 或 spark-submit
- **支持模式**：SQL 模式（spark-sql -f）和 PySpark 模式（spark-submit）

## 6. Airflow 选型说明

- **定位**：数据任务编排平台
- **职责**：DataX 任务、Spark 任务的流程管理和统一执行
- **集成方式**：DataMind 直连 Airflow REST API
- **API 能力**：
  - `GET /api/v1/dags` — DAG 列表
  - `POST /api/v1/dags/{dag_id}/dagRuns` — 触发执行（传参数）
  - `GET /api/v1/dagRuns/{run_id}` — 查询状态
  - `GET /api/v1/dagRuns/{run_id}/taskInstances/logs` — 获取日志
- **DAG 机制**：预置模板 + 参数触发（不动态生成 DAG 代码）

## 7. Doris 选型说明

- **定位**：实时分析型数据仓库
- **职责**：高性能 OLAP 查询、实时分析、AI 数据应用
- **集成方式**：DataMind 通过 MySQL 协议直连（端口 9030）
- **管理 API**：HTTP API（端口 8030）用于库表管理
- **数仓分层**：先建 ODS/DWD/DWS/ADS 结构，用模拟数据验证链路

## 8. Cube 选型说明

- **定位**：指标语义层
- **职责**：统一企业指标口径，将业务指标映射到数据模型，为 BI 和 AI Agent 提供统一查询接口
- **集成方式**：DataMind 直连 Cube REST API
- **API 能力**：
  - `POST /cubejs-api/v1/load` — 查询指标数据
  - `GET /cubejs-api/v1/meta` — 获取指标模型元数据

## 9. OpenMetadata 选型说明

- **定位**：数据治理平台
- **职责**：管理数据资产、元数据、数据血缘、数据质量和责任人信息
- **集成方式**：DataMind 直连 OpenMetadata REST API
- **API 能力**：
  - `GET /api/v1/tables` — 数据表目录
  - `GET /api/v1/lineage` — 血缘关系
  - `POST /api/v1/metadata/json` — 元数据导入

## 10. 中台开发技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5 | 前端框架 |
| TypeScript | 5 | 类型系统 |
| Element Plus | - | UI 组件库 |
| ECharts | - | 图表库 |
| Python | 3.12 | 后端语言 |
| FastAPI | 0.115+ | Web 框架 |
| SQLAlchemy | 2.x | ORM |
| PostgreSQL | 16 | 业务数据库 |
| Redis | 7.2 | 缓存 |
| APScheduler | - | 状态轮询 |

## 11. 部署方案

### DataMind 自身部署（4 个服务）

开发环境：Docker Compose 部署 frontend + backend + postgres + redis。

生产环境：推荐 Docker/Kubernetes 部署上述 4 个服务。

### 外部组件（已独立部署）

Doris、Airflow、Spark、Cube、OpenMetadata 已独立部署，DataMind 通过网络连接其 API。

## 12. 推荐版本清单

| 组件/技术 | 版本 |
|-----------|------|
| Vue | 3.5 |
| TypeScript | 5 |
| Python | 3.12 |
| FastAPI | 0.115+ |
| DataX | 3.0 |
| Spark | 3.5.3 |
| Airflow | 2.10 |
| Doris | 3.0 |
| Cube | 1.3 |
| OpenMetadata | 1.8 |
| PostgreSQL | 16 |
| Redis | 7.2 |
| Docker | 27 |

## 13. Integration Layer 结构

```
integrations/
├── base.py                # 适配器抽象基类
├── airflow_client.py      # Airflow REST API 适配器
├── doris_client.py        # Doris MySQL 协议适配器
├── cube_client.py         # Cube REST API 适配器
├── openmetadata_client.py # OpenMetadata REST API 适配器
├── datax_config_gen.py    # DataX job JSON 生成器（存库，不执行）
└── spark_config_gen.py    # Spark 作业配置生成器（存库，不执行）
```

## 14. 后续扩展

增加企业语义层、本体模型和 AI Agent，实现自然语言问数、经营分析和智能决策。
