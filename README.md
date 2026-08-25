# DataMind 企业智能数据平台

DataMind 通过一套 Docker Compose 部署前端、后端、MCP、Airflow 3.3.1、PostgreSQL、Redis 与 Cube。当前正式发布基线为 `1.0.0`，版本号以根目录 `VERSION` 为准。

## 部署要求

- Docker Engine 24+ 或 Docker Desktop
- Docker Compose v2
- 最低 8 核 CPU、16 GB 内存；建议 24–32 GB 内存
- 至少 100 GB 可用磁盘

## 目录说明

```text
DataMind/
├── backend/                 FastAPI 后端、迁移和运维脚本
├── frontend/                Vue 前端及 Nginx 配置
├── cube/                    Cube 配置与语义模型
├── airflow/                 Airflow 镜像、DAG、日志、插件和初始化脚本
├── postgres/init/           PostgreSQL 首次启动数据库初始化
├── scripts/                 发布、备份、配置校验和验收脚本
├── docker-compose.prod.yml  统一部署入口
├── VERSION                  正式发布版本号
├── RELEASE.md               发布范围、验收与回滚说明
└── README.md                部署说明
```

`backups/` 属于本机数据或恢复资料，不应复制到公开代码仓库。

## 首次部署

1. 准备唯一的环境配置文件：

```powershell
Copy-Item .env.example .env
```

Linux：

```bash
cp .env.example .env
```

2. 只编辑根目录 `.env`，替换全部 `change-me`：

- DataMind/Airflow 管理员、数据库、Redis、JWT、Fernet 和 Executor 密钥
- Cube 使用的 Doris 地址、账号和密码

Cube 和后端直接共用一个 `CUBE_API_SECRET`，不需要重复填写。Fernet Key 产生加密数据后必须保持稳定。

填写后先检查配置：

```powershell
.\scripts\validate-env.ps1
```

Linux：

```bash
sh scripts/validate-env.sh
```

3. 首次部署或版本升级统一执行发布脚本。脚本会校验配置；如果已有数据库，会先自动备份，然后拉取锁定镜像、构建版本镜像、启动服务并完成验收：

```powershell
.\scripts\release.ps1
```

Linux：

```bash
sh scripts/release.sh
```

需要分步排查时可手动执行：

```powershell
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml pull postgres redis cubestore cube
docker compose -f docker-compose.prod.yml build airflow-init backend frontend
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

后端启动时自动执行 Alembic 数据库迁移。Airflow 初始化容器会先迁移 Airflow 数据库，成功后再启动 API Server、Scheduler、DAG Processor 和 Triggerer。

当前开发部署使用一个 PostgreSQL 容器、两个相互独立的数据库：

- `datamind`：DataMind 平台数据
- `airflow`：Airflow 元数据

Airflow 使用 `LocalExecutor`；任务进程由 Scheduler 在本机容器内启动。DataMind 与 Airflow 通过 `airflow/dags/` 共享 DAG 文件，不需要 SSH/SFTP。

## 访问地址

- DataMind：`http://服务器地址/`
- 后端健康检查：`http://服务器地址:8000/health`
- DataMind MCP：`http://服务器地址:8001/mcp`
- MCP健康检查：`http://服务器地址:8001/health`
- MCP能力：数据源/表/字段读取、数据域/业务过程/模型设计、SQL预览、Airflow调度、物理表目录与运行血缘、质量规则与检测、Cube建模、指标建设、数据API草稿/预览/发布、AppKey与调用监控
- Airflow：`http://服务器地址:8082`
- Airflow 健康检查：`http://服务器地址:8082/api/v2/monitor/health`
- Cube：`http://服务器地址:4000`

默认只有 PostgreSQL 固定绑定 `127.0.0.1:5432`；其他端口的监听地址和端口号可通过 `.env` 中的 `*_BIND_ADDRESS` 与 `*_PORT` 调整。正式网络应通过防火墙、VPN或反向代理限制 `8000`、`8001`、`4000` 和 `8082` 管理端口。

## 初始化管理员

首次启动前在根目录 `.env` 设置：

```dotenv
BOOTSTRAP_ADMIN=true
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=至少12位的强密码
```

确认登录成功后将 `BOOTSTRAP_ADMIN=false`，再执行：

```powershell
docker compose -f docker-compose.prod.yml up -d backend
```

## 更新部署

推荐直接执行发布脚本，它会先备份再更新。也可以单独备份和验收：

```powershell
.\scripts\backup.ps1
.\scripts\verify-release.ps1
```

Linux：

```bash
sh scripts/backup.sh
sh scripts/verify-release.sh
```

## 日常运维

```powershell
# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 停止服务但保留数据卷
docker compose -f docker-compose.prod.yml down

# 重新启动
docker compose -f docker-compose.prod.yml up -d
```

不要执行 `docker compose down -v`，它会删除 Compose 管理的数据卷。

完整的发布清单、镜像锁定策略、备份恢复和回滚步骤见 [RELEASE.md](RELEASE.md)。
