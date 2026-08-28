# DataMind 1.1.3 正式发布基线

发布日期：2026-08-28

## 1.1.3 新增与部署适配

- MCP新增经人工确认的Cube刷新工具，并使用独立的 `metrics:execute` 授权范围。
- MCP通过受限Executor重启Cube，不直接挂载Docker Socket。
- 生产部署适配Spark 3.4.4、Scala 2.12、Java 8与固定Spark容器网段。
- Airflow镜像同时包含Scala 2.12和2.13版本的OpenLineage Spark Listener。
- CubeStore固定为已在无AVX生产CPU上验证通过的镜像摘要。

## 1.1.2 修复

- 驾驶舱资产总数改为统计数据目录中状态有效的物理表。
- 新增或编辑数据源后自动执行连接测试，连接成功后立即同步该数据源的表和字段元数据。
- 数据源连接结果改为中文居中弹窗，并显示数据库版本、同步表数和字段数。
- 全局确认、取消及表单对话框统一使用中文并在屏幕中央显示。

## 1.1.1 修复

- 安装并启用 Airflow OpenLineage Listener，通过认证 HTTP Transport 将事件发送到 DataMind。
- 新增 DataMind OpenLineage RunEvent 接收端，支持 Airflow 任务事件与 Spark 子事件按 `parentRunId` 合并。
- 新增 `DorisSQLOperator` 与 `DorisSparkSubmitOperator`，显式输出 Doris 输入/输出 Dataset Facet，并为 Spark 启用 OpenLineage Listener。
- 持久化 OpenLineage Dataset namespace，避免任务完成事件覆盖 Spark 运行时采集的数据集。
- 发布校验增加 OpenLineage Provider、namespace 和 Spark Listener JAR 检查。

## 1.1.0 新增

- Airflow 3.3.1 镜像加入 Java 17 与 PySpark 4.2.0。
- 调度脚本编辑器新增 PySpark DAG 模板，默认以 `local[2]` 运行。
- DAG 保存前执行 Python AST 语法校验并识别 PySpark 依赖，避免错误脚本直接覆盖已生效文件。
- 普通 Python DAG 与 PySpark DAG 继续共用 Airflow LocalExecutor、运行日志和任务监控。

## 1.0.1 修复

- 修复 MCP 客户端新建窗口请求 200 条用户数据、超过后端 100 条分页上限，导致服务用户下拉框为空的问题。

## 发布范围

- 数据建模：数据域、业务过程、模型设计与 Cube 建模
- 数据开发：SQL 脚本、预览与 Airflow 调度
- 指标建设：指标分类、原子/派生指标、指标查询
- 数据资产：物理表目录、运行血缘、数据质量
- 数据服务：API 目录、发布、调用凭证、调用监控与接口文档
- 智能化接入：MCP 工具、资源、提示词、作用域、审计与变更集
- 基础设施：单 PostgreSQL 容器双数据库、Redis、Cube、Airflow 3.3.1 LocalExecutor

OpenMetadata、DataX、独立 Spark 集群组件和旧 ETL 页面不属于本发布版本；PySpark 仅作为 Airflow 单机任务运行时提供。

## 固化策略

- 产品版本由 `VERSION`、`.env` 中的 `APP_VERSION` 和 `DATAMIND_VERSION` 共同确定。
- DataMind 后端、MCP、执行器共用 `datamind-backend:1.1.3` 镜像。
- 前端使用 `datamind-frontend:1.1.3`，Airflow 使用 `datamind-airflow:1.1.3`。
- PostgreSQL、Redis、Cube 与 Cube Store 使用不可漂移的镜像摘要。
- Python、Airflow Provider 与前端 npm 依赖均使用锁定版本或锁文件。
- `.env`、运行日志、Airflow 密码文件和数据库备份不纳入 Git。

## 发布

Windows：

```powershell
Copy-Item .env.example .env
# 编辑 .env 并替换全部 change-me，仅首次部署需要复制
.\scripts\release.ps1
```

Linux：

```bash
cp .env.example .env
# 编辑 .env 并替换全部 change-me，仅首次部署需要复制
sh scripts/release.sh
```

发布脚本依次执行配置校验、已有数据库备份、锁定镜像拉取、版本镜像构建、容器更新和发布验收。

## 验收标准

- Compose 配置可以解析，12 个常驻服务全部运行。
- DataMind、后端、MCP、Cube、Airflow 健康接口全部返回 HTTP 200。
- 后端报告版本 `1.1.3`。
- Alembic 当前数据库版本为唯一 `head`。
- PostgreSQL 备份文件大于 1 KB，并生成 SHA-256 校验文件。

执行：

```powershell
.\scripts\verify-release.ps1
```

## 备份与恢复

备份：

```powershell
.\scripts\backup.ps1
```

恢复属于覆盖性操作，先停止除 PostgreSQL 外的服务，并确认目标备份文件：

```powershell
docker compose -f docker-compose.prod.yml stop backend mcp-server executor airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer
Get-Content -Raw backups\datamind-YYYYMMDD-HHMMSS.sql | docker compose -f docker-compose.prod.yml exec -T postgres psql -U datamind -d postgres
docker compose -f docker-compose.prod.yml up -d
.\scripts\verify-release.ps1
```

恢复前必须另做一次当前库备份。不要执行 `docker compose down -v`。

## 应用回滚

1. 保留当前数据库卷并备份数据库。
2. 将代码切换到目标发布标签。
3. 将 `.env` 的 `APP_VERSION` 与 `DATAMIND_VERSION` 调整为目标版本。
4. 执行目标版本的发布脚本。
5. 只有在数据库迁移不向后兼容时，才使用同版本备份恢复数据库。

当前仓库没有远程地址；本地发布提交和标签需要单独推送到正式 Git 仓库后，其他服务器才能通过 Git 复现部署。
