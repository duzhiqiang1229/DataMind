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
  list(params: { page: number; page_size: number; source_type?: string }) {
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
  testConnection(id: string) {
    return request.post(`/datasources/${id}/test`);
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
  list(params: { page: number; page_size: number; layer?: string; status?: string }) {
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
  delete(id: string) {
    return request.delete(`/data-models/${id}`);
  },
  versions(id: string) {
    return request.get(`/data-models/${id}/versions`);
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

export { authApi as default };
