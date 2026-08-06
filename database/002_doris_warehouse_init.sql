-- ============================================================
-- Doris 数仓分层初始化 (MVP - 模拟数据)
-- ============================================================

-- ODS 层: 原始数据 (从业务系统同步)
CREATE DATABASE IF NOT EXISTS ods;
USE ods;

-- ODS 用户表
CREATE TABLE IF NOT EXISTS ods_user (
    user_id      BIGINT NOT NULL,
    username     VARCHAR(50),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    status       INT,
    create_time  DATETIME,
    update_time  DATETIME
) DISTRIBUTED BY HASH(user_id) BUCKETS 4
  PROPERTIES("replication_num" = "1");

-- ODS 订单表
CREATE TABLE IF NOT EXISTS ods_order (
    order_id     BIGINT NOT NULL,
    user_id      BIGINT,
    order_amount  DECIMAL(12,2),
    order_status INT,
    create_time  DATETIME,
    update_time  DATETIME
) DISTRIBUTED BY HASH(order_id) BUCKETS 4
  PROPERTIES("replication_num" = "1");

-- ODS 商品表
CREATE TABLE IF NOT EXISTS ods_product (
    product_id   BIGINT NOT NULL,
    product_name VARCHAR(200),
    category     VARCHAR(50),
    price        DECIMAL(10,2),
    create_time  DATETIME
) DISTRIBUTED BY HASH(product_id) BUCKETS 4
  PROPERTIES("replication_num" = "1");


-- DWD 层: 明细数据 (清洗 + 规范化)
CREATE DATABASE IF NOT EXISTS dwd;
USE dwd;

CREATE TABLE IF NOT EXISTS dwd_user_fact (
    user_id      BIGINT NOT NULL,
    username     VARCHAR(50),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    status       VARCHAR(20),     -- active/inactive (清洗后)
    is_valid     BOOLEAN DEFAULT TRUE,
    create_time  DATETIME,
    update_time  DATETIME
) DISTRIBUTED BY HASH(user_id) BUCKETS 4
  PROPERTIES("replication_num" = "1");

CREATE TABLE IF NOT EXISTS dwd_order_detail (
    order_id      BIGINT NOT NULL,
    user_id       BIGINT,
    order_amount  DECIMAL(12,2),
    order_status  VARCHAR(20),
    create_date   DATE,
    create_hour   TINYINT,
    update_time   DATETIME
) DISTRIBUTED BY HASH(order_id) BUCKETS 4
  PROPERTIES("replication_num" = "1");


-- DWS 层: 聚合数据 (按主题汇总)
CREATE DATABASE IF NOT EXISTS dws;
USE dws;

CREATE TABLE IF NOT EXISTS dws_user_daily (
    stat_date     DATE NOT NULL,
    new_users     BIGINT,
    active_users  BIGINT,
    total_users   BIGINT
) DISTRIBUTED BY HASH(stat_date) BUCKETS 2
  PROPERTIES("replication_num" = "1");

CREATE TABLE IF NOT EXISTS dws_order_daily (
    stat_date       DATE NOT NULL,
    order_count     BIGINT,
    total_amount    DECIMAL(15,2),
    avg_amount      DECIMAL(10,2),
    paid_count      BIGINT
) DISTRIBUTED BY HASH(stat_date) BUCKETS 2
  PROPERTIES("replication_num" = "1");


-- ADS 层: 应用数据 (面向展示)
CREATE DATABASE IF NOT EXISTS ads;
USE ads;

CREATE TABLE IF NOT EXISTS ads_dashboard_summary (
    stat_date      DATE NOT NULL,
    total_users    BIGINT,
    new_users_today BIGINT,
    total_orders   BIGINT,
    revenue_today  DECIMAL(15,2),
    avg_order_amt  DECIMAL(10,2)
) DISTRIBUTED BY HASH(stat_date) BUCKETS 1
  PROPERTIES("replication_num" = "1");


-- ============================================================
-- 模拟数据 (用于验证链路)
-- ============================================================

INSERT INTO ods.ods_user VALUES
    (1, 'zhangsan', 'zhang@example.com', '13800000001', 1, '2026-07-01 10:00:00', '2026-07-01 10:00:00'),
    (2, 'lisi',     'lisi@example.com',   '13800000002', 1, '2026-07-15 14:00:00', '2026-07-15 14:00:00'),
    (3, 'wangwu',   'wang@example.com',  '13800000003', 0, '2026-08-01 09:00:00', '2026-08-01 09:00:00');

INSERT INTO ods.ods_order VALUES
    (1001, 1, 299.00, 2, '2026-08-01 10:30:00', '2026-08-01 10:30:00'),
    (1002, 1, 159.50, 2, '2026-08-02 15:00:00', '2026-08-02 15:00:00'),
    (1003, 2, 899.00, 1, '2026-08-03 11:00:00', '2026-08-03 11:00:00'),
    (1004, 3, 49.00,  0, '2026-08-04 16:00:00', '2026-08-04 16:00:00');

INSERT INTO ods.ods_product VALUES
    (1, 'DataMind企业版', '软件', 9900.00, '2026-06-01 00:00:00'),
    (2, 'DataMind标准版', '软件', 4900.00, '2026-06-01 00:00:00'),
    (3, '数据咨询服务',    '服务', 2000.00, '2026-06-15 00:00:00');
