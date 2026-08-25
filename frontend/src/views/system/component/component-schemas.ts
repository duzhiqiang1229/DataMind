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
    description: "Apache Airflow — 工作流调度引擎，管理平台调度任务 DAG",
    icon: "Timer",
    hasHttpApi: true,
    fields: [
      {
        key: "base_url",
        label: "REST API 地址",
        type: "text",
        placeholder: "http://localhost:8082",
        default: "http://localhost:8082",
        required: true,
        store: "base_url",
        help: "Airflow 3 API Server 根地址（不要带 /api/v2，Compose 内部会自动使用服务名）",
        pattern: /^https?:\/\/\S+$/i,
        patternMessage: "请输入有效的 URL，如 http://192.168.1.4:8082",
        group: "connection",
      },
      {
        key: "auth_type",
        label: "认证方式",
        type: "select",
        default: "airflow_jwt",
        store: "auth_type",
        options: [
          { label: "Airflow 3 JWT（账号密码）", value: "airflow_jwt" },
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
        showWhenAuth: "airflow_jwt",
        group: "credentials",
      },
      {
        key: "password",
        label: "密码",
        type: "password",
        placeholder: "",
        default: "",
        store: "credentials",
        showWhenAuth: "airflow_jwt",
        group: "credentials",
      },
      {
        key: "api_version",
        label: "API 版本",
        type: "select",
        default: "3",
        store: "config",
        options: [
          { label: "Airflow 3 Public API v2", value: "3" },
        ],
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

};

/** Order for display in the grid */
export const COMPONENT_ORDER = ["airflow", "cube"];
