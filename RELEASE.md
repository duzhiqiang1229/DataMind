# DataMind 1.0.1 正式发布基线

发布日期：2026-08-25

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

OpenMetadata、DataX、Spark 和旧 ETL 页面不属于本发布版本。

## 固化策略

- 产品版本由 `VERSION`、`.env` 中的 `APP_VERSION` 和 `DATAMIND_VERSION` 共同确定。
- DataMind 后端、MCP、执行器共用 `datamind-backend:1.0.1` 镜像。
- 前端使用 `datamind-frontend:1.0.1`，Airflow 使用 `datamind-airflow:1.0.1`。
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
- 后端报告版本 `1.0.1`。
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
