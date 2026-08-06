import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { setToken, getToken } from "@/api/token";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/login/index.vue"),
    meta: { title: "登录", public: true },
  },
  {
    path: "/",
    component: () => import("@/layouts/MainLayout.vue"),
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/dashboard/index.vue"),
        meta: { title: "首页驾驶舱", icon: "Odometer" },
      },
      {
        path: "datasource",
        name: "DataSource",
        component: () => import("@/views/datasource/index.vue"),
        meta: { title: "数据源管理", icon: "Coin" },
      },
      {
        path: "datax",
        name: "DataXTasks",
        component: () => import("@/views/datax/index.vue"),
        meta: { title: "DataX 同步", icon: "Sort" },
      },
      {
        path: "spark",
        name: "SparkTasks",
        component: () => import("@/views/spark/index.vue"),
        meta: { title: "Spark 任务", icon: "Cpu" },
      },
      {
        path: "query",
        name: "QueryWorkbench",
        component: () => import("@/views/query/index.vue"),
        meta: { title: "SQL 工作台", icon: "Monitor" },
      },
      {
        path: "data-model",
        name: "DataModels",
        component: () => import("@/views/data-model/index.vue"),
        meta: { title: "数据模型", icon: "Files" },
      },
      {
        path: "publish",
        name: "Publish",
        component: () => import("@/views/publish/index.vue"),
        meta: { title: "发布管理", icon: "Promotion" },
      },
      {
        path: "warehouse/browse",
        name: "WarehouseBrowse",
        component: () => import("@/views/warehouse/browse/index.vue"),
        meta: { title: "库表浏览", icon: "FolderOpened" },
      },
      {
        path: "warehouse/storage",
        name: "StorageMonitor",
        component: () => import("@/views/warehouse/storage/index.vue"),
        meta: { title: "存储监控", icon: "Coin" },
      },
      {
        path: "metrics",
        name: "MetricsCenter",
        component: () => import("@/views/metrics/index.vue"),
        meta: { title: "指标中心", icon: "DataAnalysis" },
      },
      {
        path: "assets/catalog",
        name: "DataCatalog",
        component: () => import("@/views/assets/catalog/index.vue"),
        meta: { title: "数据目录", icon: "Collection" },
      },
      {
        path: "assets/lineage",
        name: "DataLineage",
        component: () => import("@/views/assets/lineage/index.vue"),
        meta: { title: "血缘关系", icon: "Share" },
      },
      {
        path: "data-service",
        name: "DataService",
        component: () => import("@/views/data-service/index.vue"),
        meta: { title: "数据服务", icon: "Share" },
      },
      {
        path: "system/user",
        name: "UserManagement",
        component: () => import("@/views/system/user/index.vue"),
        meta: { title: "用户管理", icon: "User" },
      },
      {
        path: "system/role",
        name: "RoleManagement",
        component: () => import("@/views/system/role/index.vue"),
        meta: { title: "角色管理", icon: "UserFilled" },
      },
      {
        path: "system/permission",
        name: "PermissionManagement",
        component: () => import("@/views/system/permission/index.vue"),
        meta: { title: "权限管理", icon: "Key" },
      },
      {
        path: "system/component",
        name: "ComponentConfig",
        component: () => import("@/views/system/component/index.vue"),
        meta: { title: "组件配置", icon: "Connection" },
      },
      {
        path: "system/config",
        name: "SystemConfig",
        component: () => import("@/views/system/config/index.vue"),
        meta: { title: "系统配置", icon: "Tools" },
      },
      {
        path: "system/log",
        name: "OperationLog",
        component: () => import("@/views/system/log/index.vue"),
        meta: { title: "操作日志", icon: "Document" },
      },
      {
        path: "schedule/monitor",
        name: "TaskMonitor",
        component: () => import("@/views/schedule/monitor/index.vue"),
        meta: { title: "任务监控", icon: "Timer" },
      },
      {
        path: "schedule/dag",
        name: "DagManagement",
        component: () => import("@/views/schedule/dag/index.vue"),
        meta: { title: "DAG 管理", icon: "Connection" },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/views/not-found/index.vue"),
    meta: { title: "页面不存在", public: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation guard: check auth
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  document.title = `${to.meta.title || ""} - DataMind`;

  if (to.meta.public) {
    next();
    return;
  }

  if (!authStore.token) {
    next({ path: "/login", query: { redirect: to.fullPath } });
    return;
  }

  // Sync module-level token (handles page refresh where Pinia restored from localStorage
  // but the in-memory token holder was reset)
  if (!getToken() && authStore.token) {
    setToken(authStore.token);
  }

  // Load user info if not loaded
  if (!authStore.userInfo) {
    try {
      await authStore.fetchCurrentUser();
    } catch {
      authStore.logout();
      next({ path: "/login" });
      return;
    }
  }

  next();
});

export default router;
