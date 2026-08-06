# DataMind 项目记忆

## 项目概述
- **项目名称**: DataMind企业智能平台
- **定位**: 数据工程师工作台 + 企业智能数据平台
- **目标**: 建设统一的数据采集、加工、存储、指标、治理、服务和AI分析能力
- **核心组件**: DataX 3.0(同步), Spark 3.5.3(计算), Airflow 2.10(调度), Doris 3.0(数仓), Cube 1.3(指标语义), OpenMetadata 1.8(治理)

## 技术栈
- **前端**: Vue 3.5 + TypeScript + Element Plus + ECharts
- **后端**: Python 3.12 + FastAPI + SQLAlchemy 2.x + Pydantic 2.x
- **业务DB**: PostgreSQL 16, 缓存: Redis 7.2, 认证: JWT
- **部署**: Docker Compose(开发) / Kubernetes(生产)

## 架构分层
1. 数据源层(ERP/CRM/OA)
2. 数据集成层(DataX)
3. 数据计算层(Spark)
4. 数据仓库层(Doris, ODS/DWD/DWS/ADS)
5. 语义指标层(Cube)
6. 数据治理层(OpenMetadata)
7. 应用服务层(BI/API/AI Agent)

## 功能模块(10个一级菜单)
1. 首页驾驶舱 2. 数据管理中心 3. 数据开发中心 4. 调度中心 5. 数据仓库中心
6. 数据资产中心 7. 指标中心 8. 数据服务中心 9. 系统管理 10. AI智能分析中心(未来)

## MVP路线
- Phase1: 基础平台(门户/权限/框架)
- Phase2: 数据集成与开发(DataX/Spark/Airflow)
- Phase3: 指标服务(Cube/API)
- Phase4: 数据治理(OpenMetadata)
- Phase5: AI智能分析(语义层/AI Agent)

## 团队与项目状态
- **团队规模**: 1-2人小团队
- **团队背景**: 数据方向(非前后端开发为主)
- **项目状态**: Phase1 MVP已启动,基础平台跑通(登录+权限+布局+首页)
- **数据情况**: 先用测试数据验证
- **最终目标**: 交付产品给客户用

## 开发环境状态(2026-08-06)
- **Docker**: PostgreSQL 15 (port 5432) + Redis 7.2 (port 6379)
- **后端**: FastAPI on http://localhost:8000 (68路由, uvicorn --reload)
- **前端**: Vite dev server on http://localhost:5173 (proxy /api → :8000)
- **数据库**: 21张表, seed数据完成(admin/admin123, 4角色, 21权限, 22菜单, 5配置)
- **Python venv**: C:/Users/wanying/.workbuddy/binaries/python/envs/default/Scripts/python.exe
- **Node**: C:/Users/wanying/.workbuddy/binaries/node/versions/22.22.2/node.exe
- **已知问题**: 系统HTTP_PROXY=127.0.0.1:7890未关闭,命令需前缀HTTP_PROXY= HTTPS_PROXY=
- **已修复**: greenlet缺失, bcrypt5.0不兼容, ResponseOK泛型, pinia版本冲突, token读取方式, seed幂等

## 组件集成方案(需求沟通确认)
- **外部组件状态**: 6大组件均已独立部署,DataMind通过API连接
- **DataMind自部署**: 仅Vue前端 + FastAPI后端 + PostgreSQL + Redis
- **Integration Layer**: 4个适配器(airflow/doris/cube/openmetadata) + 2个配置生成器(datax/spark)
- **前端方案**: 从零自建Vue(不用Admin框架)
- **Airflow DAG机制**: 预置模板+参数触发(Airflow里放固定DAG模板,DataMind REST API传参触发)
- **组件配置存储**: PostgreSQL component_config表 + UI可视化管理(地址/端口/认证信息)
- **DataX配置**: DataMind生成job JSON存库,触发时传给Airflow DAG执行
- **Spark配置**: 支持SQL+PySpark脚本,DataMind存储SQL/脚本文件+提交参数,触发时传Airflow
- **任务状态同步**: 定时轮询Airflow REST API(如每10秒),更新到本地库

## 开发计划(需求沟通确认)
- **设计细化程度**: 先细化核心表结构和接口schema到可编码程度,确认后再开工
- **MVP开发范围**: 登录+权限+布局+首页+数据源管理+DataX同步+Doris查询+系统管理(先跑通一条完整数据链路)
- **Doris数仓**: 先建ODS/DWD/DWS/ADS分层结构,用模拟数据验证,后续接入真实数据源
- **执行链路**: DataMind存配置 → REST API触发Airflow DAG模板(传参数) → Airflow执行 → DataMind轮询状态

## 技术方案细化(已完成,可编码)
- **后端工程**: backend/app/ 目录,含core/api/v1/services/integrations/models/schemas/utils
- **数据库**: database/001_init_schema.sql (16张表DDL) + 002_doris_warehouse_init.sql (数仓分层+模拟数据)
- **Airflow**: airflow-dags/datax_sync_dag.py + spark_job_dag.py (预置模板+参数触发)
- **前端工程**: frontend/src/ 目录,含api/layouts/router/stores/views(6个页面)
- **技术设计文档**: TECH_DESIGN.md (工程结构/分层/表清单/接口清单/DAG/前端页面)
- **工程结构**: backend/ + frontend/ + database/ + airflow-dags/

## 文档清单(13份, 位于docs/)
PRD需求文档, 产品信息架构设计, 代码工程设计规范, 前端UI原型设计说明书, 后端服务设计文档,
开发实施计划与里程碑, 接口设计文档, 数据库设计文档, 系统架构设计文档, 组件选型方案,
详细功能设计说明书, 运维管理方案, 部署实施方案
