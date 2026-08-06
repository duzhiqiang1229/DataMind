import axios, { type AxiosRequestConfig } from "axios";
import { ElMessage } from "element-plus";
import NProgress from "nprogress";
import { getToken, clearToken } from "./token";

const instance = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach JWT token from module-level holder
instance.interceptors.request.use(
  (config) => {
    NProgress.start();
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    NProgress.done();
    return Promise.reject(error);
  }
);

// Response interceptor: unwrap data, handle errors
instance.interceptors.response.use(
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
        clearToken();
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

// Typed wrapper: interceptor unwraps response.data.data, so return Promise<T>
const request = {
  get: <T = any>(url: string, config?: AxiosRequestConfig) => instance.get(url, config) as unknown as Promise<T>,
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => instance.post(url, data, config) as unknown as Promise<T>,
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => instance.put(url, data, config) as unknown as Promise<T>,
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => instance.delete(url, config) as unknown as Promise<T>,
};

export default request;
