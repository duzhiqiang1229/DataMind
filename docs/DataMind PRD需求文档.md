# DataMind 企业智能平台 PRD 需求文档

> 版本：v2.0 | 更新日期：2026-08-06  
> 变更说明：基于需求沟通确认，更新组件集成方式为 API 连接模式，调整 MVP 范围与执行架构

---

## 1. 产品概述

- **产品名称**：DataMind 企业智能平台
- **建设目标**：建设统一的数据管理、开发、治理、服务和智能分析平台，通过 API 连接已部署的 DataX、Spark、Airflow、Doris、Cube、OpenMetadata 六大开源组件，形成企业级数据能力中心
- **目标用户**：数据工程师、数据分析师、业务人员、管理人员

## 2. 产品定位

DataMind 企业智能平台作为企业数据基础设施的**统一控制层**，不替代底层数据组件能力，而是通过组件 API 进行连接、配置和使用，提供数据采集、数据加工、数据仓库、指标管理、数据治理、数据服务以及 AI 智能分析能力。

**核心定位**：
- DataMind 不负责部署底层组件，组件已独立部署
- DataMind 通过 REST API / MySQL 协议连接各组件
- DataMind 自身仅需部署：Vue 前端 + FastAPI 后端 + PostgreSQL + Redis

## 3. 产品总体架构

```
用户 → DataMind 平台门户 → FastAPI 后端服务 → 外部组件 API
                                         ↓
                    ┌────────────────────┼────────────────────┐
                    ↓                    ↓                    ↓
              Airflow REST API    Doris MySQL协议    Cube/OpenMetadata REST API
              (执行引擎)          (查询引擎)         (指标/治理)
                    ↓
              DataX CLI / Spark Submit
```

核心组件及集成方式：

| 组件 | 职责 | 集成方式 | API 类型 |
|------|------|---------|---------|
| DataX | 数据同步 | 通过 Airflow DAG 执行 DataX CLI | 无原生 API，Airflow 代执行 |
| Spark | 数据加工计算 | 通过 Airflow DAG 提交 spark-submit | 无原生 API，Airflow 代执行 |
| Airflow | 任务调度编排 | DataMind 直连 REST API | REST API（完善） |
| Doris | 数据仓库 OLAP 分析 | DataMind 直连 MySQL 协议 | MySQL 协议（端口 9030）+ HTTP API（端口 8030） |
| Cube | 指标语义管理 | DataMind 直连 REST API | REST API（完善） |
| OpenMetadata | 元数据治理 | DataMind 直连 REST API | REST API（完善） |

## 4. 功能模块规划

### 4.1 数据源管理中心

管理企业业务数据库、文件、接口等数据源。

功能：
- 数据源新增、修改、删除
- 数据源连接测试
- 数据源权限管理

### 4.2 数据集成中心

基于 DataX 实现数据同步，通过 Airflow 统一执行。

功能：
- 同步任务创建（配置源表/目标表/字段映射）
- DataMind 生成 DataX job JSON 并存入 PostgreSQL
- 触发 Airflow DAG 执行 DataX（预置模板 + 参数触发）
- 全量/增量配置
- 同步日志查看（轮询 Airflow API 获取状态）

### 4.3 数据开发中心

提供企业数据工程开发能力，支持 SQL 和 PySpark 两种开发模式。

功能：
- SQL 开发（通过 Doris MySQL 协议直连查询）
- PySpark 脚本开发
- Spark 任务管理（配置存库，Airflow 触发执行）
- 数据模型管理（ODS/DWD/DWS/ADS 模型设计、表结构设计、字段设计、模型版本管理）
- 数据加工流程管理
- 发布管理（发布版本管理、发布记录查看、发布状态跟踪）
- 开发版本管理

### 4.4 调度中心

基于 Airflow 实现任务编排，DataMind 通过 REST API 管理。

功能：
- DAG 流程管理（预置模板，参数触发）
- 定时调度
- 任务监控（定时轮询 Airflow API，约 10 秒间隔）
- 失败重试
- 运行日志查看（通过 Airflow API 获取日志）

### 4.5 数据仓库中心

基于 Doris 建设企业分析型数据仓库，DataMind 通过 MySQL 协议直连。

功能：
- ODS 数据管理
- DWD 明细模型
- DWS 主题模型
- ADS 应用模型
- SQL 查询服务

数仓分层先行建设，使用模拟数据验证链路。

### 4.6 指标中心

基于 Cube 建设企业指标语义层，DataMind 通过 REST API 集成。

功能：
- 指标定义
- 指标口径管理
- 指标维度管理
- 指标 API 服务
- 指标血缘分析

示例：销售额 = 订单金额 - 退款金额

### 4.7 数据治理中心

基于 OpenMetadata 实现数据资产治理，DataMind 通过 REST API 集成。

功能：
- 数据目录
- 元数据管理
- 数据血缘
- 数据质量规则
- 数据责任人管理

### 4.8 数据服务中心

为外部系统和 AI 应用提供数据能力。

功能：
- API 管理
- 数据查询服务
- 权限控制
- 服务调用记录

### 4.9 AI 智能分析扩展

通过企业语义层和 AI Agent 实现自然语言数据分析。

流程：用户问题 → AI Agent → 企业语义层 → Cube → Doris → 分析结果

## 5. 用户角色

| 角色 | 职责 |
|------|------|
| 数据工程师 | 数据开发、任务管理、模型建设 |
| 数据管理员 | 数据治理和权限管理 |
| 分析师 | 使用指标和数据服务 |
| 业务人员 | 智能问数和经营分析 |

## 6. 非功能需求

- **性能要求**：支持大规模数据查询和并发分析
- **安全要求**：支持用户权限（RBAC）、数据权限、操作审计
- **扩展要求**：支持 Docker/Kubernetes 部署

## 7. MVP 建设路线

### MVP 第一阶段（核心链路）

> 目标：跑通一条完整数据链路 + 管理界面

- 登录 + RBAC 权限体系
- 首页驾驶舱
- 数据源管理 + DataX 同步
- Doris SQL 查询工作台
- 系统管理（用户/角色/权限）

### 第二阶段（扩展）

- Spark 任务管理
- Airflow 调度管理
- Cube 指标中心
- OpenMetadata 治理入口

### 第三阶段（智能化）

- 企业语义层
- AI Agent
- 智能问数

## 8. 关键架构决策

| 决策点 | 结论 |
|--------|------|
| 组件部署 | 6 大组件已独立部署，DataMind 通过 API 连接 |
| DataMind 自部署 | Vue 前端 + FastAPI 后端 + PostgreSQL + Redis |
| Airflow DAG 机制 | 预置模板 + 参数触发（不动态生成 DAG 代码） |
| 组件配置存储 | PostgreSQL + UI 管理（component_config 表） |
| DataX 配置管理 | DataMind 生成 job JSON 存库，触发时传给 Airflow |
| Spark 配置管理 | 支持 SQL + PySpark 脚本，存库后传给 Airflow |
| 任务状态同步 | 定时轮询 Airflow API（约 10 秒间隔） |
| 前端方案 | 从零自建 Vue3 + TS + Element Plus |
| Integration Layer | 4 适配器 + 2 配置生成器 |
| Doris 数仓 | 先建 ODS/DWD/DWS/ADS 分层，用模拟数据验证 |
