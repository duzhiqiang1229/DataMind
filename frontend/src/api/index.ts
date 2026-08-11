import request from "./request";

// ============================================================
// Auth API
// ============================================================
export const authApi = {
  login(username: string, password: string) {
    return request.post("/auth/login", { username, password });
  },
  refreshToken(refreshToken: string) {
    return request.post("/auth/refresh", { refresh_token: refreshToken });
  },
  getCurrentUser() {
    return request.get("/auth/me");
  },
  logout() {
    return request.post("/auth/logout");
  },
};

// ============================================================
// Data Source API
// ============================================================
export const datasourceApi = {
  list(params: { page: number; page_size: number; keyword?: string; source_type?: string; status?: string }) {
    return request.get("/datasources", { params });
  },
  create(data: any) {
    return request.post("/datasources", data);
  },
  update(id: string, data: any) {
    return request.put(`/datasources/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/datasources/${id}`);
  },
  listDatabases(id: string) {
    return request.get(`/datasources/${id}/databases`);
  },
  testConnection(id: string) {
    return request.post(`/datasources/${id}/test`);
  },
  query(id: string, sql: string, limit: number) {
    return request.post(`/datasources/${id}/query`, { sql, limit });
  },
  getTables(id: string, schema?: string) {
    return request.get(`/datasources/${id}/tables`, { params: { schema } });
  },
  getColumns(id: string, tableName: string, schema?: string) {
    return request.get(`/datasources/${id}/tables/${tableName}/columns`, { params: { schema } });
  },
};

// ============================================================
// DataX Task API
// ============================================================
export const dataxApi = {
  list(params: { page: number; page_size: number; status?: string }) {
    return request.get("/datax-tasks", { params });
  },
  create(data: any) {
    return request.post("/datax-tasks", data);
  },
  detail(id: string) {
    return request.get(`/datax-tasks/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/datax-tasks/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/datax-tasks/${id}`);
  },
  trigger(id: string) {
    return request.post(`/datax-tasks/${id}/trigger`, { run_immediately: true });
  },
  pause(id: string) {
    return request.post(`/datax-tasks/${id}/pause`);
  },
  resume(id: string) {
    return request.post(`/datax-tasks/${id}/resume`);
  },
  instances(id: string, params: { page: number; page_size: number }) {
    return request.get(`/datax-tasks/${id}/instances`, { params });
  },
  instanceStatus(instanceId: string) {
    return request.get(`/datax-tasks/instances/${instanceId}/status`);
  },
  instanceLog(instanceId: string) {
    return request.get(`/datax-tasks/instances/${instanceId}/log`);
  },
};

// ============================================================
// Spark Task API
// ============================================================
export const sparkApi = {
  list(params: { page: number; page_size: number; status?: string }) {
    return request.get("/spark-tasks", { params });
  },
  create(data: any) {
    return request.post("/spark-tasks", data);
  },
  detail(id: string) {
    return request.get(`/spark-tasks/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/spark-tasks/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/spark-tasks/${id}`);
  },
  trigger(id: string) {
    return request.post(`/spark-tasks/${id}/trigger`, { run_immediately: true });
  },
  instances(id: string, params: { page: number; page_size: number }) {
    return request.get(`/spark-tasks/${id}/instances`, { params });
  },
  instanceStatus(instanceId: string) {
    return request.get(`/spark-tasks/instances/${instanceId}/status`);
  },
  instanceLog(instanceId: string) {
    return request.get(`/spark-tasks/instances/${instanceId}/log`);
  },
};

// ============================================================
// Data Model API
// ============================================================
export const dataModelApi = {
  list(params: { page: number; page_size: number; keyword?: string; layer?: string; status?: string; business_domain?: string; data_domain?: string }) {
    return request.get("/data-models", { params });
  },
  create(data: any) {
    return request.post("/data-models", data);
  },
  detail(id: string) {
    return request.get(`/data-models/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/data-models/${id}`, data);
  },
  publish(id: string) {
    return request.post(`/data-models/${id}/publish`);
  },
  delete(id: string) {
    return request.delete(`/data-models/${id}`);
  },
  versions(id: string) {
    return request.get(`/data-models/${id}/versions`);
  },
  businessDomains() {
    return request.get("/data-models/business-domains");
  },
  createBusinessDomain(data: any) {
    return request.post("/data-models/business-domains", data);
  },
  updateBusinessDomain(id: string, data: any) {
    return request.put(`/data-models/business-domains/${id}`, data);
  },
  deleteBusinessDomain(id: string) {
    return request.delete(`/data-models/business-domains/${id}`);
  },
  dataDomains() {
    return request.get("/data-models/data-domains");
  },
  createDataDomain(data: any) {
    return request.post("/data-models/data-domains", data);
  },
  updateDataDomain(id: string, data: any) {
    return request.put(`/data-models/data-domains/${id}`, data);
  },
  deleteDataDomain(id: string) {
    return request.delete(`/data-models/data-domains/${id}`);
  },
};

// ============================================================
// Publish API
// ============================================================
export const publishApi = {
  list(params: { page: number; page_size: number; publish_type?: string; status?: string }) {
    return request.get("/publish", { params });
  },
  create(data: any) {
    return request.post("/publish", data);
  },
  detail(id: string) {
    return request.get(`/publish/${id}`);
  },
  execute(id: string) {
    return request.post(`/publish/${id}/execute`);
  },
  delete(id: string) {
    return request.delete(`/publish/${id}`);
  },
};

// ============================================================
// Doris Query API
// ============================================================
export const queryApi = {
  execute(sql: string, database?: string, limit?: number) {
    return request.post("/doris-query/execute", { sql, database, limit });
  },
  listDatabases() {
    return request.get("/doris-query/databases");
  },
  listTables(database: string) {
    return request.get(`/doris-query/databases/${database}/tables`);
  },
  getTableSchema(database: string, table: string) {
    return request.get(`/doris-query/databases/${database}/tables/${table}/columns`);
  },
  savedQueries(params: { page: number; page_size: number }) {
    return request.get("/doris-query/saved", { params });
  },
  saveQuery(data: { query_name: string; sql_text: string; database?: string; description?: string; tags?: string }) {
    return request.post("/doris-query/saved", data);
  },
  deleteSavedQuery(id: string) {
    return request.delete(`/doris-query/saved/${id}`);
  },
  history(params: { page: number; page_size: number }) {
    return request.get("/doris-query/history", { params });
  },
};

// ============================================================
// Component Config API
// ============================================================
export const componentApi = {
  list(params: { page: number; page_size: number }) {
    return request.get("/components", { params });
  },
  listAll() {
    return request.get("/components/all");
  },
  getByCode(code: string) {
    return request.get(`/components/by-code/${code}`);
  },
  upsertByCode(code: string, data: any) {
    return request.put(`/components/by-code/${code}`, data);
  },
  create(data: any) {
    return request.post("/components", data);
  },
  update(id: string, data: any) {
    return request.put(`/components/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/components/${id}`);
  },
  healthCheck(code: string) {
    return request.post(`/components/${code}/health-check`);
  },
};

// ============================================================
// Role API
// ============================================================
export const roleApi = {
  list() {
    return request.get("/roles");
  },
  create(data: any) {
    return request.post("/roles", data);
  },
  update(id: string, data: any) {
    return request.put(`/roles/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/roles/${id}`);
  },
  assignPermissions(id: string, permission_ids: string[]) {
    return request.put(`/roles/${id}/permissions`, { permission_ids });
  },
  assignMenus(id: string, menu_ids: string[]) {
    return request.put(`/roles/${id}/menus`, { menu_ids });
  },
  listPermissions() {
    return request.get("/roles/permissions");
  },
};

// ============================================================
// Menu API
// ============================================================
export const menuApi = {
  tree() {
    return request.get("/menus/tree");
  },
  create(data: any) {
    return request.post("/menus", data);
  },
  update(id: string, data: any) {
    return request.put(`/menus/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/menus/${id}`);
  },
};

// ============================================================
// User API
// ============================================================
export const userApi = {
  list(params: { page: number; page_size: number; keyword?: string; status?: string }) {
    return request.get("/users", { params });
  },
  create(data: any) {
    return request.post("/users", data);
  },
  detail(id: string) {
    return request.get(`/users/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/users/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/users/${id}`);
  },
  resetPassword(id: string, new_password: string) {
    return request.post(`/users/${id}/reset-password`, { new_password });
  },
  toggleStatus(id: string) {
    return request.post(`/users/${id}/toggle-status`);
  },
  assignRoles(id: string, role_ids: string[]) {
    return request.put(`/users/${id}/roles`, { role_ids });
  },
};

// ============================================================
// Dashboard API
// ============================================================
export const dashboardApi = {
  stats() {
    return request.get("/dashboard/stats");
  },
  recentTasks(limit = 10) {
    return request.get("/dashboard/recent-tasks", { params: { limit } });
  },
  taskInstances(params: { page: number; page_size: number; task_type?: string; status?: string }) {
    return request.get("/dashboard/task-instances", { params });
  },
  componentStatus() {
    return request.get("/dashboard/component-status");
  },
};

// ============================================================
// System API
// ============================================================
export const systemApi = {
  listConfigs() {
    return request.get("/system/configs");
  },
  updateConfig(key: string, value: any) {
    return request.put(`/system/configs/${key}`, { config_value: value });
  },
  logs(params: { page: number; page_size: number; module?: string }) {
    return request.get("/system/logs", { params });
  },
};

// ============================================================
// Cube Metrics API
// ============================================================
export const cubeApi = {
  meta() {
    return request.get("/cube/meta");
  },
  load(query: any) {
    return request.post("/cube/load", query);
  },
  health() {
    return request.get("/cube/health");
  },
};

// ============================================================
// Cube Modeling API
// ============================================================
export const cubeModelApi = {
  entities() {
    return request.get("/cube-model/entities");
  },
  getCube(name: string) {
    return request.get(`/cube-model/cubes/${name}`);
  },
  saveCube(data: any) {
    return request.post("/cube-model/cubes", data);
  },
  deleteCube(name: string) {
    return request.delete(`/cube-model/cubes/${name}`);
  },
  saveView(data: any) {
    return request.post("/cube-model/views", data);
  },
  deleteView(name: string) {
    return request.delete(`/cube-model/views/${name}`);
  },
  refresh() {
    return request.post("/cube-model/refresh");
  },
};

// ============================================================
// Metric Definition API
// ============================================================
export const metricDefinitionApi = {
  list(params: { page: number; page_size: number; keyword?: string; category_id?: string }) {
    return request.get("/metric-definitions", { params });
  },
  create(data: any) {
    return request.post("/metric-definitions", data);
  },
  update(id: string, data: any) {
    return request.put(`/metric-definitions/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/metric-definitions/${id}`);
  },
};

// ============================================================
// OpenMetadata API
// ============================================================
export const openmetadataApi = {
  databases(limit = 100) {
    return request.get("/openmetadata/databases", { params: { limit } });
  },
  tables(database?: string, limit = 100) {
    return request.get("/openmetadata/tables", { params: { database, limit } });
  },
  tableDetail(fqn: string) {
    return request.get(`/openmetadata/tables/${fqn}`);
  },
  lineage(fqn: string, entity_type = "table") {
    return request.get("/openmetadata/lineage", { params: { fqn, entity_type } });
  },
  search(q: string, limit = 20) {
    return request.get("/openmetadata/search", { params: { q, limit } });
  },
  assets(params: { q?: string; entity_type?: string; page?: number; page_size?: number } = {}) {
    return request.get("/openmetadata/assets", { params });
  },
  summary() {
    return request.get("/openmetadata/summary");
  },
  governance(limit = 100) {
    return request.get("/openmetadata/governance", { params: { limit } });
  },
  quality(table_fqn?: string, limit = 100) {
    return request.get("/openmetadata/quality", { params: { table_fqn, limit } });
  },
  health() {
    return request.get("/openmetadata/health");
  },
};

// ============================================================
// Data Service API
// ============================================================
export const dataServiceApi = {
  list(params: { page: number; page_size: number; status?: string }) {
    return request.get("/data-services", { params });
  },
  create(data: any) {
    return request.post("/data-services", data);
  },
  detail(id: string) {
    return request.get(`/data-services/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/data-services/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/data-services/${id}`);
  },
  execute(id: string, params: Record<string, any>) {
    return request.post(`/data-services/${id}/execute`, { params });
  },
};

// ============================================================
// Airflow API
// ============================================================
export const airflowApi = {
  listDags(limit = 100, offset = 0) {
    return request.get("/airflow", { params: { limit, offset } });
  },
  getDag(dagId: string) {
    return request.get(`/airflow/${dagId}`);
  },
  createDagFile(data: { script_name: string; content: string }) {
    return request.post("/airflow/dag-files", data);
  },
  getDagFile(dagId: string) {
    return request.get(`/airflow/${dagId}/file`);
  },
  updateDagFile(dagId: string, content: string) {
    return request.put(`/airflow/${dagId}/file`, { content });
  },
  pauseDag(dagId: string) {
    return request.post(`/airflow/${dagId}/pause`);
  },
  resumeDag(dagId: string) {
    return request.post(`/airflow/${dagId}/resume`);
  },
  triggerDag(dagId: string, conf: any = {}) {
    return request.post(`/airflow/${dagId}/trigger`, { conf });
  },
  listDagRuns(dagId: string, limit = 50, offset = 0) {
    return request.get(`/airflow/${dagId}/runs`, { params: { limit, offset } });
  },
  getDagRunDetail(dagId: string, runId: string) {
    return request.get(`/airflow/${dagId}/runs/${runId}`);
  },
  getDagRunLog(dagId: string, runId: string, taskId: string, tryNumber = 1) {
    return request.get(`/airflow/${dagId}/runs/${runId}/log`, { params: { task_id: taskId, try_number: tryNumber } });
  },
  retryDagRun(dagId: string, runId: string, taskId: string) {
    return request.post(`/airflow/${dagId}/runs/${runId}/retry`, { task_id: taskId });
  },
  deployDags() {
    return request.post("/airflow/deploy-dags");
  },
  createDag(data: any) {
    return request.post("/airflow/create-dag", data);
  },
  dagRuns(params: { page: number; page_size: number; dag_id?: string; status?: string }) {
    return request.get("/airflow/dag-runs", { params });
  },
  syncRuns() {
    return request.post("/airflow/sync-runs");
  },
};

// ============================================================
// DAG Workflow API (multi-task orchestration)
// ============================================================
export const dagWorkflowApi = {
  list(params: { page: number; page_size: number }) {
    return request.get("/dag-workflows", { params });
  },
  create(data: any) {
    return request.post("/dag-workflows", data);
  },
  detail(id: string) {
    return request.get(`/dag-workflows/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/dag-workflows/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/dag-workflows/${id}`);
  },
  deploy(id: string) {
    return request.post(`/dag-workflows/${id}/deploy`);
  },
};

// ============================================================
// ETL Script API (multi-language script development)
// ============================================================
export const etlScriptApi = {
  list(params: { page: number; page_size: number; language?: string; keyword?: string }) {
    return request.get("/etl-scripts", { params });
  },
  create(data: any) {
    return request.post("/etl-scripts", data);
  },
  detail(id: string) {
    return request.get(`/etl-scripts/${id}`);
  },
  update(id: string, data: any) {
    return request.put(`/etl-scripts/${id}`, data);
  },
  delete(id: string) {
    return request.delete(`/etl-scripts/${id}`);
  },
  execute(id: string, params: any) {
    return request.post(`/etl-scripts/${id}/execute`, params);
  },
  deploySchedule(id: string) {
    return request.post(`/etl-scripts/${id}/deploy-schedule`);
  },
};

// ============================================================
// Doris Storage API
// ============================================================
export const dorisStorageApi = {
  overview() {
    return request.get("/doris-query/storage");
  },
  tableStats(database: string, table: string) {
    return request.get(`/doris-query/databases/${database}/tables/${table}/stats`);
  },
  partitions(database: string, table: string) {
    return request.get(`/doris-query/databases/${database}/tables/${table}/partitions`);
  },
};

// ============================================================
// Metric Category API
// ============================================================
export const metricCategoryApi = {
  list() { return request.get("/metric-categories"); },
  create(data: any) { return request.post("/metric-categories", data); },
  update(id: string, data: any) { return request.put(`/metric-categories/${id}`, data); },
  delete(id: string) { return request.delete(`/metric-categories/${id}`); },
  listMetrics(categoryId: string) { return request.get(`/metric-categories/${categoryId}/metrics`); },
  assignMetric(categoryId: string, data: any) { return request.post(`/metric-categories/${categoryId}/metrics`, data); },
  listUnmapped() { return request.get("/metric-categories/unmapped"); },
};

// ============================================================
// Table Owner API
// ============================================================
export const tableOwnerApi = {
  list(params: { page: number; page_size: number; database_name?: string }) { return request.get("/table-owners", { params }); },
  setOwner(data: any) { return request.post("/table-owners", data); },
  getOwner(database: string, table: string) { return request.get(`/table-owners/${database}/${table}`); },
  removeOwner(database: string, table: string) { return request.delete(`/table-owners/${database}/${table}`); },
};

// ============================================================
// Data Service Log API
// ============================================================
export const dataServiceLogApi = {
  logs(apiId: string, params: { page: number; page_size: number }) { return request.get(`/data-services/${apiId}/logs`, { params }); },
  callStats(days = 7) { return request.get("/data-services/call-stats", { params: { days } }); },
  permissions(apiId: string) { return request.get(`/data-services/${apiId}/permissions`); },
  assignPermission(apiId: string, data: any) { return request.post(`/data-services/${apiId}/permissions`, data); },
  revokePermission(apiId: string, roleId: string) { return request.delete(`/data-services/${apiId}/permissions/${roleId}`); },
};

export { authApi as default };
