/**
 * 每个外部组件的专属配置表单 schema。
 * 组件不同，配置项不同 — 不再用通用 JSON 文本框，而是结构化字段。
 */

export type FieldType = "text" | "number" | "password" | "select" | "textarea";

export interface FormField {
  key: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  default: string | number | boolean;
  required?: boolean;
  options?: { label: string; value: string }[];
  /** load options dynamically (e.g. connected data sources) */
  dynamicOptions?: "datasources";
  help?: string;
  /** store in config_json (default) or credentials (encrypted) */
  store: "config" | "credentials" | "base_url" | "auth_type";
  /** show only when auth_type matches this value */
  showWhenAuth?: string;
  group: "connection" | "credentials" | "advanced";
  /** numeric range validation (for number fields) */
  min?: number;
  max?: number;
  /** regex validation */
  pattern?: RegExp;
  patternMessage?: string;
}

export interface ComponentSchema {
  code: string;
  name: string;
  type: string;
  description: string;
  icon: string;
  /** if false, no base_url/auth_type fields shown */
  hasHttpApi: boolean;
  fields: FormField[];
}

export const COMPONENT_SCHEMAS: Record<string, ComponentSchema> = {
  airflow: {
    code: "airflow",
    name: "Airflow 调度服务",
    type: "scheduler",
    description: "Apache Airflow — 工作流调度引擎，管理 DataX/Spark 任务 DAG",
    icon: "Timer",
    hasHttpApi: true,
    fields: [
      {
        key: "base_url",
        label: "REST API 地址",
        type: "text",
        placeholder: "http://localhost:8080",
        default: "http://localhost:8080",
        required: true,
        store: "base_url",
        help: "Airflow Web Server 根地址（不要带 /api/v1，后端会自动拼接）",
        pattern: /^https?:\/\/\S+$/i,
        patternMessage: "请输入有效的 URL，如 http://192.168.1.4:8082",
        group: "connection",
      },
      {
        key: "auth_type",
        label: "认证方式",
        type: "select",
        default: "basic",
        store: "auth_type",
        options: [
          { label: "Basic Auth (账号密码)", value: "basic" },
          { label: "Token", value: "token" },
          { label: "无认证", value: "none" },
        ],
        group: "connection",
      },
      {
        key: "username",
        label: "用户名",
        type: "text",
        placeholder: "admin",
        default: "",
        store: "credentials",
        showWhenAuth: "basic",
        group: "credentials",
      },
      {
        key: "password",
        label: "密码",
        type: "password",
        placeholder: "",
        default: "",
        store: "credentials",
        showWhenAuth: "basic",
        group: "credentials",
      },
      {
        key: "token",
        label: "API Token",
        type: "text",
        placeholder: "Airflow API Token",
        default: "",
        store: "credentials",
        showWhenAuth: "token",
        group: "credentials",
      },
      {
        key: "api_version",
        label: "API 版本",
        type: "select",
        default: "2",
        store: "config",
        options: [
          { label: "Stable API v2", value: "2" },
          { label: "Experimental API v1", value: "1" },
        ],
        group: "advanced",
      },
      {
        key: "dags_folder",
        label: "DAG 文件目录",
        type: "text",
        placeholder: "/opt/airflow/dags",
        default: "/opt/airflow/dags",
        store: "config",
        help: "Airflow DAG 文件存放路径（用于 DataMind 写入 DAG 模板）",
        group: "advanced",
      },
      {
        key: "ssh_host",
        label: "SSH 主机",
        type: "text",
        placeholder: "192.168.1.4",
        default: "192.168.1.4",
        store: "config",
        help: "Airflow 所在服务器地址（用于自动部署 DAG）",
        group: "advanced",
      },
      {
        key: "ssh_user",
        label: "SSH 用户",
        type: "text",
        placeholder: "root",
        default: "root",
        store: "config",
        group: "advanced",
      },
      {
        key: "ssh_password",
        label: "SSH 密码",
        type: "password",
        placeholder: "SSH 登录密码",
        default: "",
        store: "config",
        help: "用于 SFTP 上传 DAG 模板到 Airflow 服务器",
        group: "advanced",
      },
      {
        key: "dags_path",
        label: "DAGS 部署目录",
        type: "text",
        placeholder: "/opt/software/airflow/dags",
        default: "/opt/software/airflow/dags",
        store: "config",
        help: "Airflow dags 目录，DataMind 自动部署 DAG 模板到此路径",
        group: "advanced",
      },
    ],
  },

  cube: {
    code: "cube",
    name: "Cube 语义指标引擎",
    type: "semantic",
    description: "Cube.js — 语义层和指标引擎，提供统一的指标定义和 API",
    icon: "DataAnalysis",
    hasHttpApi: true,
    fields: [
      {
        key: "base_url",
        label: "Cube API 地址",
        type: "text",
        placeholder: "http://localhost:4000",
        default: "http://localhost:4000",
        required: true,
        store: "base_url",
        help: "Cube.js 根地址（不要带 /cubejs-api，后端会自动拼接）",
        pattern: /^https?:\/\/\S+$/i,
        patternMessage: "请输入有效的 URL，如 http://192.168.1.4:4000",
        group: "connection",
      },
      {
        key: "auth_type",
        label: "认证方式",
        type: "select",
        default: "token",
        store: "auth_type",
        options: [
          { label: "Token", value: "token" },
          { label: "无认证", value: "none" },
        ],
        group: "connection",
      },
      {
        key: "datasource_id",
        label: "数据源",
        type: "select",
        default: "",
        store: "config",
        dynamicOptions: "datasources",
        help: "选择「数据管理 → 数据源管理」中已连接测试通过的数据源，保存后自动应用到 Cube 容器（需本机 Docker 可用）",
        group: "connection",
      },
      {
        key: "token",
        label: "API Token",
        type: "text",
        placeholder: "Cube API Secret",
        default: "",
        store: "credentials",
        showWhenAuth: "token",
        group: "credentials",
      },
      {
        key: "dev_mode",
        label: "开发模式",
        type: "select",
        default: "true",
        store: "config",
        options: [
          { label: "开启", value: "true" },
          { label: "关闭", value: "false" },
        ],
        help: "开发模式下 Cube 会自动刷新 schema",
        group: "advanced",
      },
    ],
  },

  openmetadata: {
    code: "openmetadata",
    name: "OpenMetadata 治理平台",
    type: "governance",
    description: "OpenMetadata — 数据资产治理平台，管理元数据、血缘、数据质量",
    icon: "Files",
    hasHttpApi: true,
    fields: [
      {
        key: "base_url",
        label: "API 地址",
        type: "text",
        placeholder: "http://localhost:8585",
        default: "http://localhost:8585",
        required: true,
        store: "base_url",
        help: "OpenMetadata Server 根地址（不要带 /api，后端会自动拼接）",
        pattern: /^https?:\/\/\S+$/i,
        patternMessage: "请输入有效的 URL，如 http://192.168.1.4:8585",
        group: "connection",
      },
      {
        key: "auth_type",
        label: "认证方式",
        type: "select",
        default: "token",
        store: "auth_type",
        options: [
          { label: "JWT Token", value: "token" },
          { label: "无认证", value: "none" },
        ],
        group: "connection",
      },
      {
        key: "jwt_token",
        label: "JWT Token",
        type: "text",
        placeholder: "OpenMetadata JWT Token",
        default: "",
        store: "credentials",
        showWhenAuth: "token",
        group: "credentials",
      },
      {
        key: "api_version",
        label: "API 版本",
        type: "text",
        placeholder: "v1",
        default: "v1",
        store: "config",
        group: "advanced",
      },
    ],
  },

  datax: {
    code: "datax",
    name: "DataX 数据同步",
    type: "etl",
    description: "DataX — 阿里开源离线数据同步工具，通过命令行执行同步任务",
    icon: "Switch",
    hasHttpApi: false,
    fields: [
      {
        key: "datax_home",
        label: "DataX 安装目录",
        type: "text",
        placeholder: "/opt/datax",
        default: "/opt/datax",
        required: true,
        store: "config",
        help: "DataX 的安装路径，用于定位 datax.py 脚本",
        group: "connection",
      },
      {
        key: "python_path",
        label: "Python 路径",
        type: "text",
        placeholder: "/usr/bin/python2",
        default: "/usr/bin/python2",
        store: "config",
        help: "执行 DataX 使用的 Python 解释器路径（DataX 需要 Python 2）",
        group: "connection",
      },
      {
        key: "jvm_params",
        label: "JVM 参数",
        type: "text",
        placeholder: "-Xms1g -Xmx2g",
        default: "-Xms1g -Xmx2g",
        store: "config",
        help: "DataX 执行时的 JVM 参数",
        group: "advanced",
      },
      {
        key: "temp_dir",
        label: "文件目录",
        type: "text",
        placeholder: "/tmp/datax",
        default: "/tmp/datax",
        store: "config",
        help: "任务发布时 DataX job JSON 文件的存放路径（后端自动写入该目录）",
        group: "advanced",
      },
      {
        key: "ssh_host",
        label: "SSH 主机",
        type: "text",
        placeholder: "192.168.1.4",
        default: "192.168.1.4",
        store: "config",
        help: "DataX 所在服务器地址（用于发布 job 文件和执行任务）",
        group: "advanced",
      },
      {
        key: "ssh_user",
        label: "SSH 用户",
        type: "text",
        placeholder: "root",
        default: "root",
        store: "config",
        group: "advanced",
      },
      {
        key: "ssh_password",
        label: "SSH 密码",
        type: "password",
        placeholder: "SSH 登录密码",
        default: "",
        store: "config",
        group: "advanced",
      },
    ],
  },

  spark: {
    code: "spark",
    name: "Spark 计算引擎",
    type: "compute",
    description: "Apache Spark — 大规模数据处理引擎，执行 Spark SQL 和 PySpark 任务",
    icon: "Cpu",
    hasHttpApi: false,
    fields: [
      {
        key: "spark_home",
        label: "Spark 安装目录",
        type: "text",
        placeholder: "/opt/spark",
        default: "/opt/spark",
        required: true,
        store: "config",
        help: "Spark 的安装路径",
        group: "connection",
      },
      {
        key: "master_url",
        label: "Master URL",
        type: "text",
        placeholder: "spark://localhost:7077",
        default: "spark://localhost:7077",
        store: "config",
        help: "Spark Master 地址（standalone 模式）",
        group: "connection",
      },
      {
        key: "deploy_mode",
        label: "部署模式",
        type: "select",
        default: "client",
        store: "config",
        options: [
          { label: "Client", value: "client" },
          { label: "Cluster", value: "cluster" },
        ],
        help: "Spark 任务的部署模式",
        group: "advanced",
      },
      {
        key: "executor_memory",
        label: "Executor 内存",
        type: "text",
        placeholder: "2g",
        default: "2g",
        store: "config",
        group: "advanced",
      },
      {
        key: "driver_memory",
        label: "Driver 内存",
        type: "text",
        placeholder: "1g",
        default: "1g",
        store: "config",
        group: "advanced",
      },
    ],
  },
};

/** Order for display in the grid */
export const COMPONENT_ORDER = ["airflow", "cube", "openmetadata", "datax", "spark"];
