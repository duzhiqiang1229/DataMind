import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/api";

export interface UserInfo {
  id: string;
  username: string;
  full_name: string | null;
  email: string | null;
  avatar: string | null;
  department: string | null;
  roles: string[];
  permissions: string[];
  menus: MenuTree[];
}

export interface MenuTree {
  id: string;
  menu_name: string;
  menu_type: string;
  route_path: string;
  component: string;
  icon: string;
  sort_order: number;
  children: MenuTree[];
}

export const useAuthStore = defineStore("auth", () => {
  // State (persisted: token, refreshToken)
  const token = ref<string>("");
  const refreshToken = ref<string>("");
  const userInfo = ref<UserInfo | null>(null);

  // Getters
  const isLoggedIn = computed(() => !!token.value);
  const permissions = computed(() => userInfo.value?.permissions || []);
  const roles = computed(() => userInfo.value?.roles || []);

  const hasPermission = (code: string) => {
    if (roles.value.includes("admin")) return true;
    return permissions.value.includes(code);
  };

  // Actions
  async function login(username: string, password: string) {
    const res = await authApi.login(username, password);
    token.value = res.access_token;
    refreshToken.value = res.refresh_token;
  }

  async function fetchCurrentUser() {
    userInfo.value = await authApi.getCurrentUser();
  }

  function logout() {
    token.value = "";
    refreshToken.value = "";
    userInfo.value = null;
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    permissions,
    roles,
    hasPermission,
    login,
    fetchCurrentUser,
    logout,
  };
}, {
  persist: {
    pick: ["token", "refreshToken"],
  },
});
