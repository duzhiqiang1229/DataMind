import axios, { type AxiosInstance, type AxiosRequestConfig } from "axios";
import { ElMessage } from "element-plus";
import NProgress from "nprogress";

const request: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach JWT token
request.interceptors.request.use(
  (config) => {
    NProgress.start();
    // Pinia persisted state stores under store id "auth" as JSON
    const raw = localStorage.getItem("auth");
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed.token) {
          config.headers.Authorization = `Bearer ${parsed.token}`;
        }
      } catch {
        // ignore parse errors
      }
    }
    return config;
  },
  (error) => {
    NProgress.done();
    return Promise.reject(error);
  }
);

// Response interceptor: unwrap data, handle errors
request.interceptors.response.use(
  (response) => {
    NProgress.done();
    const data = response.data;

    // Direct return for blob/stream responses
    if (response.config.responseType === "blob") {
      return response;
    }

    // Standard response: { code, message, data }
    if (data.code !== undefined && data.code !== 200) {
      ElMessage.error(data.message || "请求失败");
      return Promise.reject(new Error(data.message));
    }

    return data.data !== undefined ? data.data : data;
  },
  (error) => {
    NProgress.done();

    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail || error.response.data?.message;

      if (status === 401) {
        ElMessage.error("登录已过期，请重新登录");
        // Clear Pinia persisted auth state
        localStorage.removeItem("auth");
        window.location.href = "/login";
      } else if (status === 403) {
        ElMessage.error("没有权限执行此操作");
      } else if (status >= 500) {
        ElMessage.error(detail || "服务器错误");
      } else {
        ElMessage.error(detail || `请求错误 (${status})`);
      }
    } else if (error.code === "ECONNABORTED") {
      ElMessage.error("请求超时");
    } else {
      ElMessage.error("网络连接失败");
    }

    return Promise.reject(error);
  }
);

export default request;
