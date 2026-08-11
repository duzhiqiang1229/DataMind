# OpenMetadata 试运行环境

此目录基于 OpenMetadata 官方 `1.12.6` Docker Compose 模板，并由
项目根目录的 `docker-compose.prod.yml` 通过 Compose `include` 合并到同一个
`datamind` 项目中。

```powershell
Copy-Item openmetadata/.env.example openmetadata/.env
# 替换 .env 中的所有占位密码和 Fernet Key
docker compose -f docker-compose.prod.yml up -d
```

- OpenMetadata UI: http://localhost:8585
- 采集服务（Airflow）: http://localhost:8080
- OpenMetadata 与 DataMind 共用 `postgres` 容器，使用独立的
  `openmetadata_db` 和 `airflow_db` 数据库；首次启动会自动创建数据库和专用账号，
  PostgreSQL 不暴露宿主机端口。
- Elasticsearch 仍为 OpenMetadata 提供资产检索，且不暴露宿主机端口。
- Docker Desktop 中所有服务统一归属 `datamind` 项目。
- OpenMetadata Server 同时加入 `datamind_default` 网络，DataMind 后端通过
  `http://openmetadata-server:8585` 访问。

当前为单机试运行配置，不等同于生产高可用部署。请使用独立强密码，并为 DataMind
创建最小权限 Bot Token。两个 Fernet Key 在产生加密数据后必须保持稳定。
