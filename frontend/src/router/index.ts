import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";

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
        path: "query",
        name: "QueryWorkbench",
        component: () => import("@/views/query/index.vue"),
        meta: { title: "SQL 工作台", icon: "Monitor" },
      },
      {
        path: "system/user",
        name: "UserManagement",
        component: () => import("@/views/system/user/index.vue"),
        meta: { title: "用户管理", icon: "User" },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/views/login/index.vue"),
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
