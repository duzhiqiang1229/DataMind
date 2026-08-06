-- ============================================================
-- DataMind Platform Database Schema (MVP)
-- PostgreSQL 16
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. RBAC 用户权限体系
-- ============================================================

-- 用户表
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) UNIQUE,
    phone           VARCHAR(20),
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(50),
    avatar          VARCHAR(500),
    department      VARCHAR(100),
    status          VARCHAR(20) NOT NULL DEFAULT 'active',  -- active/disabled
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS '平台用户表';
COMMENT ON COLUMN users.status IS 'active=启用, disabled=禁用';

-- 角色表
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_code   VARCHAR(50) NOT NULL UNIQUE,          -- admin, data_engineer, analyst
    role_name   VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    status      VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 权限表
CREATE TABLE permissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permission_code VARCHAR(100) NOT NULL UNIQUE,     -- datax:task:create, doris:query:execute
    permission_name VARCHAR(100) NOT NULL,
    resource        VARCHAR(50) NOT NULL,             -- datax, doris, datasource, user...
    action          VARCHAR(20) NOT NULL,             -- view, create, update, delete, execute
    description     VARCHAR(200),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 用户-角色关联表
CREATE TABLE user_roles (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id    UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- 角色-权限关联表
CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

-- 菜单表 (前端路由 + 按钮权限)
CREATE TABLE menus (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id   UUID REFERENCES menus(id) ON DELETE CASCADE,
    menu_name   VARCHAR(50) NOT NULL,
    menu_type   VARCHAR(20) NOT NULL,                 -- directory/menu/button
    route_path  VARCHAR(200),                        -- /datax/tasks
    component   VARCHAR(200),                        -- datax/TaskList
    icon         VARCHAR(100),
    sort_order   INT NOT NULL DEFAULT 0,
    visible      BOOLEAN NOT NULL DEFAULT TRUE,
    status       VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 角色-菜单关联表
CREATE TABLE role_menus (
    role_id    UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    menu_id    UUID NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, menu_id)
);

-- 索引
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);
CREATE INDEX idx_menus_parent ON menus(parent_id);


-- ============================================================
-- 2. 组件配置管理
-- ============================================================

-- 外部组件连接配置
CREATE TABLE component_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_code  VARCHAR(50) NOT NULL UNIQUE,     -- airflow, doris, cube, openmetadata
    component_name  VARCHAR(100) NOT NULL,            -- Airflow 调度服务
    component_type  VARCHAR(50) NOT NULL,             -- scheduler, olap, semantic, governance
    base_url        VARCHAR(255) NOT NULL,           -- http://airflow-host:8080
    config_json     JSONB NOT NULL DEFAULT '{}',     -- 非敏感配置: mysql_host, mysql_port, http_port...
    auth_type       VARCHAR(20) NOT NULL DEFAULT 'none',  -- none/token/basic
    credentials_encrypted TEXT,                       -- 加密的敏感信息: password, token (Fernet加密)
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    last_check_at   TIMESTAMPTZ,
    last_check_ok   BOOLEAN,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE component_configs IS '外部组件连接配置(Airflow/Doris/Cube/OpenMetadata)';
COMMENT ON COLUMN component_configs.config_json IS '非敏感配置JSON,如Doris的mysql_host/mysql_port/http_port';
COMMENT ON COLUMN component_configs.credentials_encrypted IS 'Fernet加密的敏感凭据JSON';

CREATE INDEX idx_component_configs_type ON component_configs(component_type);
CREATE INDEX idx_component_configs_status ON component_configs(status);


-- ============================================================
-- 3. 数据源管理
-- ============================================================

CREATE TABLE data_sources (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name         VARCHAR(100) NOT NULL,        -- 生产ERP数据库
    source_type         VARCHAR(30) NOT NULL,         -- mysql/oracle/postgresql/sqlserver
    host                VARCHAR(255) NOT NULL,
    port                INT NOT NULL,
    database_name       VARCHAR(100),
    username            VARCHAR(100) NOT NULL,
    password_encrypted  TEXT NOT NULL,               -- Fernet加密
    default_schema      VARCHAR(100),
    description         VARCHAR(500),
    status              VARCHAR(20) NOT NULL DEFAULT 'active',  -- active/inactive
    last_connection_test TIMESTAMPTZ,
    last_connection_ok  BOOLEAN,
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE data_sources IS '外部数据源配置(用于DataX同步的源端)';

CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_status ON data_sources(status);


-- ============================================================
-- 4. DataX 同步任务
-- ============================================================

-- DataX 任务定义
CREATE TABLE datax_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name       VARCHAR(200) NOT NULL,
    task_code       VARCHAR(100) NOT NULL UNIQUE,    -- sync_erp_user_to_doris

    -- 源端配置
    source_datasource_id UUID NOT NULL REFERENCES data_sources(id),
    source_table         VARCHAR(200) NOT NULL,      -- ods.ods_user
    source_schema        VARCHAR(100),
    where_clause         TEXT,                         -- 增量条件: update_time >= '${last_sync_time}'
    split_pk             VARCHAR(100),                 -- 分片字段: id

    -- 目标配置 (Doris)
    target_database      VARCHAR(100) NOT NULL,       -- ods
    target_table         VARCHAR(200) NOT NULL,       -- ods_user
    target_type          VARCHAR(20) NOT NULL DEFAULT 'doris',

    -- DataX job JSON (由 datax_config_gen 生成)
    job_config          JSONB NOT NULL,                -- 完整的 DataX job JSON

    -- 同步选项
    sync_mode           VARCHAR(20) NOT NULL DEFAULT 'full',  -- full/incremental
    channel             INT NOT NULL DEFAULT 3,
    error_limit_record  INT NOT NULL DEFAULT 0,
    error_limit_pct     NUMERIC(5,4) NOT NULL DEFAULT 0.02,

    -- 调度配置
    schedule_cron       VARCHAR(100),                  -- Airflow DAG cron 表达式 (0 2 * * *)
    dag_id              VARCHAR(100),                  -- 对应的 Airflow DAG ID
    is_paused           BOOLEAN NOT NULL DEFAULT TRUE,

    status              VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft/active/paused/archived
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE datax_tasks IS 'DataX数据同步任务定义';
COMMENT ON COLUMN datax_tasks.job_config IS '由datax_config_gen生成的完整DataX job JSON';

CREATE INDEX idx_datax_tasks_status ON datax_tasks(status);
CREATE INDEX idx_datax_tasks_source ON datax_tasks(source_datasource_id);
CREATE INDEX idx_datax_tasks_dag ON datax_tasks(dag_id);

-- DataX 字段映射表
CREATE TABLE datax_field_mappings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         UUID NOT NULL REFERENCES datax_tasks(id) ON DELETE CASCADE,
    source_column   VARCHAR(200) NOT NULL,
    target_column   VARCHAR(200) NOT NULL,
    source_type     VARCHAR(100),                     -- VARCHAR(50), BIGINT...
    target_type     VARCHAR(100),                     -- VARCHAR(50), BIGINT...
    is_primary_key  BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE datax_field_mappings IS 'DataX同步字段映射';

CREATE INDEX idx_datax_field_mappings_task ON datax_field_mappings(task_id);


-- ============================================================
-- 5. 任务执行实例 (Airflow DAG Run 同步)
-- ============================================================

CREATE TABLE task_instances (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type       VARCHAR(20) NOT NULL,             -- datax/spark
    task_id         UUID NOT NULL,                    -- 关联 datax_tasks.id 或 spark_tasks.id
    dag_id          VARCHAR(100) NOT NULL,            -- datax_sync / spark_job
    dag_run_id      VARCHAR(200) NOT NULL,            -- Airflow 返回的 run_id

    -- 执行参数快照 (触发时的 conf)
    run_config      JSONB,

    -- 状态
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued/running/success/failed
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    duration_seconds INT,

    -- 同步统计 (仅 DataX)
    rows_read       BIGINT,
    rows_written    BIGINT,
    bytes_written   BIGINT,

    -- 触发者
    triggered_by    UUID REFERENCES users(id),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE task_instances IS '任务执行实例(映射Airflow DAG Run)';

CREATE INDEX idx_task_instances_status ON task_instances(status);
CREATE INDEX idx_task_instances_task ON task_instances(task_type, task_id);
CREATE INDEX idx_task_instances_dag_run ON task_instances(dag_run_id);
CREATE INDEX idx_task_instances_created ON task_instances(created_at DESC);


-- ============================================================
-- 5.5 数据模型管理
-- ============================================================

-- 数据模型 (ODS/DWD/DWS/ADS 模型设计)
CREATE TABLE data_models (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name      VARCHAR(100) NOT NULL,
    model_code      VARCHAR(100) NOT NULL UNIQUE,
    layer           VARCHAR(20) NOT NULL,                -- ods/dwd/dws/ads
    database        VARCHAR(50) NOT NULL,                -- Doris 数据库名
    table_name      VARCHAR(100) NOT NULL,                -- Doris 表名
    description     TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft/published/archived
    current_version INT NOT NULL DEFAULT 1,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE data_models IS '数据模型管理(ODS/DWD/DWS/ADS)';
CREATE INDEX idx_data_models_layer ON data_models(layer);
CREATE INDEX idx_data_models_status ON data_models(status);

-- 数据模型字段
CREATE TABLE data_model_fields (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id        UUID NOT NULL REFERENCES data_models(id) ON DELETE CASCADE,
    field_name      VARCHAR(100) NOT NULL,
    field_type      VARCHAR(50) NOT NULL,
    field_comment    VARCHAR(200),
    is_primary_key  BOOLEAN NOT NULL DEFAULT FALSE,
    is_partition    BOOLEAN NOT NULL DEFAULT FALSE,
    default_value   VARCHAR(200),
    sort_order      INT NOT NULL DEFAULT 0
);

COMMENT ON TABLE data_model_fields IS '数据模型字段定义';
CREATE INDEX idx_data_model_fields_model ON data_model_fields(model_id);

-- 数据模型版本
CREATE TABLE data_model_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id        UUID NOT NULL REFERENCES data_models(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    table_ddl       TEXT,                                 -- 建表 SQL
    field_snapshot  JSONB,                                -- 字段快照
    change_log      TEXT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_id, version)
);

COMMENT ON TABLE data_model_versions IS '数据模型版本历史';
CREATE INDEX idx_data_model_versions_model ON data_model_versions(model_id);

-- ============================================================
-- 5.6 发布管理
-- ============================================================

-- 发布任务
CREATE TABLE publish_tasks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    publish_name        VARCHAR(100) NOT NULL,
    publish_type        VARCHAR(20) NOT NULL,             -- model/spark_task/datax_task
    source_ids          JSONB NOT NULL DEFAULT '[]',      -- 发布对象 ID 列表
    target_environment  VARCHAR(20) NOT NULL DEFAULT 'production', -- dev/staging/production
    description         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/executing/success/failed
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at         TIMESTAMPTZ
);

COMMENT ON TABLE publish_tasks IS '发布任务管理';
CREATE INDEX idx_publish_tasks_status ON publish_tasks(status);
CREATE INDEX idx_publish_tasks_type ON publish_tasks(publish_type);

-- 发布记录
CREATE TABLE publish_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    publish_task_id     UUID NOT NULL REFERENCES publish_tasks(id) ON DELETE CASCADE,
    source_id           UUID NOT NULL,
    source_type         VARCHAR(20) NOT NULL,
    source_name         VARCHAR(100),
    result              VARCHAR(20) NOT NULL,             -- success/failed
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE publish_records IS '发布记录';
CREATE INDEX idx_publish_records_task ON publish_records(publish_task_id);


-- ============================================================
-- 6. Doris 查询管理
-- ============================================================

-- 保存的查询 (SQL 工作台书签)
CREATE TABLE saved_queries (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_name VARCHAR(200) NOT NULL,
    description TEXT,
    sql_text    TEXT NOT NULL,
    database    VARCHAR(100),
    tags        VARCHAR(500),                          -- 逗号分隔标签
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE saved_queries IS '保存的SQL查询';

CREATE INDEX idx_saved_queries_name ON saved_queries(query_name);
CREATE INDEX idx_saved_queries_creator ON saved_queries(created_by);

-- 查询历史
CREATE TABLE query_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sql_text        TEXT NOT NULL,
    database        VARCHAR(100),
    row_count       INT,
    truncated       BOOLEAN NOT NULL DEFAULT FALSE,
    elapsed_ms      INT,
    status          VARCHAR(20) NOT NULL,             -- success/error
    error_message   TEXT,
    executed_by     UUID REFERENCES users(id),
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE query_history IS 'SQL查询历史';

CREATE INDEX idx_query_history_executor ON query_history(executed_by);
CREATE INDEX idx_query_history_executed_at ON query_history(executed_at DESC);


-- ============================================================
-- 7. 系统管理
-- ============================================================

-- 系统配置 (键值对)
CREATE TABLE system_configs (
    config_key      VARCHAR(100) PRIMARY KEY,
    config_value    TEXT NOT NULL,
    config_type     VARCHAR(20) NOT NULL DEFAULT 'string', -- string/int/bool/json
    description     VARCHAR(200),
    is_editable     BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by      UUID REFERENCES users(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 操作日志
CREATE TABLE operation_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    username        VARCHAR(50),
    module          VARCHAR(50),                      -- auth/datasource/datax/doris/system
    action          VARCHAR(50),                      -- create/update/delete/execute/login
    target_type     VARCHAR(50),                     -- resource type
    target_id       VARCHAR(100),                    -- resource id
    description     TEXT,                             -- 操作描述
    request_method  VARCHAR(10),                     -- GET/POST/PUT/DELETE
    request_path    VARCHAR(500),
    request_body    TEXT,
    status_code     INT,
    ip_address      VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE operation_logs IS '用户操作审计日志';

CREATE INDEX idx_operation_logs_user ON operation_logs(user_id);
CREATE INDEX idx_operation_logs_module ON operation_logs(module);
CREATE INDEX idx_operation_logs_created ON operation_logs(created_at DESC);


-- ============================================================
-- 8. 初始化数据
-- ============================================================

-- 默认角色
INSERT INTO roles (role_code, role_name, description) VALUES
    ('admin', '系统管理员', '拥有全部权限'),
    ('data_engineer', '数据工程师', '数据源/同步/开发管理'),
    ('analyst', '数据分析师', '数据查询与分析'),
    ('viewer', '只读用户', '仅查看权限')
ON CONFLICT (role_code) DO NOTHING;

-- 默认系统配置
INSERT INTO system_configs (config_key, config_value, config_type, description) VALUES
    ('platform_name', 'DataMind', 'string', '平台名称'),
    ('platform_version', '1.0.0', 'string', '平台版本'),
    ('default_page_size', '20', 'int', '默认分页大小'),
    ('sql_query_timeout', '300', 'int', 'SQL查询超时(秒)'),
    ('sql_max_rows', '10000', 'int', 'SQL最大返回行数')
ON CONFLICT (config_key) DO NOTHING;
