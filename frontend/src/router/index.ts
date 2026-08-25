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
        path: "query",
        name: "QueryWorkbench",
        component: () => import("@/views/query/index.vue"),
        meta: { title: "数据开发", icon: "Monitor" },
      },
      {
        path: "data-modeling/domain",
        name: "DataDomain",
        component: () => import("@/views/data-model/domain/index.vue"),
        meta: { title: "数据域", icon: "Grid" },
      },
      {
        path: "data-modeling/process",
        name: "BusinessProcess",
        component: () => import("@/views/data-model/process/index.vue"),
        meta: { title: "业务过程", icon: "Guide" },
      },
      {
        path: "data-modeling/model",
        name: "DataModelDesign",
        component: () => import("@/views/data-model/index.vue"),
        meta: { title: "模型设计", icon: "Files" },
      },
      {
        path: "publish",
        name: "Publish",
        component: () => import("@/views/publish/index.vue"),
        meta: { title: "发布管理", icon: "Promotion" },
      },
      {
        path: "metrics/definitions",
        name: "MetricsDefinitions",
        component: () => import("@/views/metrics/definitions/index.vue"),
        meta: { title: "指标定义", icon: "DataAnalysis" },
      },
      {
        path: "metrics/query",
        name: "MetricsQuery",
        component: () => import("@/views/metrics/query/index.vue"),
        meta: { title: "指标查询", icon: "TrendCharts" },
      },
      {
        path: "metrics/modeling",
        name: "MetricsModeling",
        component: () => import("@/views/metrics/modeling/index.vue"),
        meta: { title: "Cube建模", icon: "SetUp" },
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
        path: "assets/quality",
        name: "DataQuality",
        component: () => import("@/views/assets/quality/index.vue"),
        meta: { title: "数据质量", icon: "CircleCheck" },
      },
      {
        path: "data-service",
        redirect: "/data-service/catalog",
      },
      {
        path: "data-service/catalog",
        name: "DataServiceCatalog",
        component: () => import("@/views/data-service/index.vue"),
        meta: { title: "服务目录", icon: "Share" },
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
        path: "system/component",
        name: "ComponentConfig",
        component: () => import("@/views/system/component/index.vue"),
        meta: { title: "组件配置", icon: "Connection" },
      },
      {
        path: "system/component/:code",
        name: "ComponentDetail",
        component: () => import("@/views/system/component/detail.vue"),
        meta: { title: "组件详情", hidden: true },
      },
      {
        path: "system/mcp",
        name: "McpManagement",
        component: () => import("@/views/system/mcp/index.vue"),
        meta: { title: "MCP管理", icon: "Cpu" },
      },
      {
        path: "schedule/monitor",
        name: "TaskMonitor",
        component: () => import("@/views/schedule/monitor/index.vue"),
        meta: { title: "任务监控", icon: "Timer" },
      },
      {
        path: "schedule/task",
        name: "ScheduleTask",
        component: () => import("@/views/schedule/task/index.vue"),
        meta: { title: "调度任务", icon: "AlarmClock" },
      },
      {
        path: "data-service/stats",
        name: "DataServiceStats",
        component: () => import("@/views/data-service/stats/index.vue"),
        meta: { title: "调用监控", icon: "TrendCharts" },
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
