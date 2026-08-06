<template>
  <el-container class="main-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <el-icon size="28"><DataLine /></el-icon>
        <span v-show="!isCollapse" class="logo-text">DataMind</span>
      </div>
      <el-scrollbar class="sidebar-scroll">
        <el-menu
          :default-active="route.path"
          :collapse="isCollapse"
          router
          class="sidebar-menu"
        >
          <!-- 首页驾驶舱 -->
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>首页驾驶舱</span>
          </el-menu-item>

          <!-- 数据管理 -->
          <el-sub-menu index="/datasource">
            <template #title>
              <el-icon><Coin /></el-icon>
              <span>数据管理</span>
            </template>
            <el-menu-item index="/datasource">数据源管理</el-menu-item>
            <el-menu-item index="/datax">DataX 同步</el-menu-item>
          </el-sub-menu>

          <!-- 数据开发 -->
          <el-sub-menu index="/dev">
            <template #title>
              <el-icon><EditPen /></el-icon>
              <span>数据开发</span>
            </template>
            <el-menu-item index="/spark">Spark 任务</el-menu-item>
            <el-menu-item index="/query">SQL 工作台</el-menu-item>
            <el-menu-item index="/data-model">数据模型</el-menu-item>
            <el-menu-item index="/publish">发布管理</el-menu-item>
          </el-sub-menu>

          <!-- 数据仓库 -->
          <el-sub-menu index="/warehouse">
            <template #title>
              <el-icon><Files /></el-icon>
              <span>数据仓库</span>
            </template>
            <el-menu-item index="/warehouse/browse">库表浏览</el-menu-item>
            <el-menu-item index="/warehouse/storage">存储监控</el-menu-item>
          </el-sub-menu>

          <!-- 调度中心 -->
          <el-sub-menu index="/schedule">
            <template #title>
              <el-icon><Timer /></el-icon>
              <span>调度中心</span>
            </template>
            <el-menu-item index="/schedule/monitor">任务监控</el-menu-item>
            <el-menu-item index="/schedule/dag">DAG 管理</el-menu-item>
          </el-sub-menu>

          <!-- 数据资产 -->
          <el-sub-menu index="/assets">
            <template #title>
              <el-icon><Collection /></el-icon>
              <span>数据资产</span>
            </template>
            <el-menu-item index="/assets/catalog">数据目录</el-menu-item>
            <el-menu-item index="/assets/lineage">血缘关系</el-menu-item>
          </el-sub-menu>

          <!-- 指标中心 -->
          <el-menu-item index="/metrics">
            <el-icon><DataAnalysis /></el-icon>
            <span>指标中心</span>
          </el-menu-item>

          <!-- 数据服务 -->
          <el-menu-item index="/data-service">
            <el-icon><Share /></el-icon>
            <span>数据服务</span>
          </el-menu-item>

          <!-- 系统管理 -->
          <el-sub-menu index="/system">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/system/user">用户管理</el-menu-item>
            <el-menu-item index="/system/role">角色管理</el-menu-item>
            <el-menu-item index="/system/permission">权限管理</el-menu-item>
            <el-menu-item index="/system/component">组件配置</el-menu-item>
            <el-menu-item index="/system/config">系统配置</el-menu-item>
            <el-menu-item index="/system/log">操作日志</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <!-- Main content -->
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <!-- 面包屑 -->
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 搜索 -->
          <el-input
            v-model="searchKeyword"
            placeholder="搜索功能..."
            :prefix-icon="Search"
            size="small"
            class="header-search"
            @keyup.enter="handleSearch"
          />
          <!-- 组件状态指示 -->
          <el-tooltip content="组件连接状态" placement="bottom">
            <el-badge :value="componentIssues" :hidden="componentIssues === 0" type="danger">
              <el-icon class="header-icon" @click="router.push('/system/component')"><Connection /></el-icon>
            </el-badge>
          </el-tooltip>
          <!-- 用户下拉 -->
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" :src="authStore.userInfo?.avatar || undefined">
                {{ authStore.userInfo?.full_name?.charAt(0) || 'A' }}
              </el-avatar>
              <span class="username">{{ authStore.userInfo?.full_name || authStore.userInfo?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <el-icon><User /></el-icon>
                  {{ authStore.userInfo?.department || '未设置' }}
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Search } from "@element-plus/icons-vue";
import { useAuthStore } from "@/stores/auth";
import { dashboardApi } from "@/api";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const isCollapse = ref(false);
const searchKeyword = ref("");
const componentIssues = ref(0);

async function loadComponentStatus() {
  try {
    const res = await dashboardApi.componentStatus();
    componentIssues.value = (res || []).filter((c: any) => !c.healthy).length;
  } catch {
    // ignore
  }
}

function handleSearch() {
  const keyword = searchKeyword.value.trim().toLowerCase();
  if (!keyword) return;
  const menuMap: Record<string, string> = {
    "数据源": "/datasource", "datax": "/datax", "同步": "/datax",
    "spark": "/spark", "sql": "/query", "查询": "/query", "工作台": "/query",
    "模型": "/data-model", "发布": "/publish", "仓库": "/warehouse/browse",
    "库表": "/warehouse/browse", "监控": "/schedule/monitor", "调度": "/schedule/monitor",
    "目录": "/assets/catalog", "血缘": "/assets/lineage", "指标": "/metrics",
    "服务": "/data-service", "用户": "/system/user", "角色": "/system/role",
    "权限": "/system/permission", "组件": "/system/component", "配置": "/system/config",
    "日志": "/system/log", "首页": "/dashboard",
  };
  for (const [key, path] of Object.entries(menuMap)) {
    if (key.toLowerCase().includes(keyword) || keyword.includes(key.toLowerCase())) {
      router.push(path);
      return;
    }
  }
}

async function handleLogout() {
  try {
    await authStore.logout();
    router.push("/login");
  } catch {
    // ignore
  }
}

onMounted(loadComponentStatus);
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
}

.sidebar {
  background: #304156;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  background: #2b3a4d;

  .logo-text {
    font-size: 18px;
    font-weight: bold;
    white-space: nowrap;
  }
}

.sidebar-scroll {
  height: calc(100vh - 60px);
}

.sidebar-menu {
  border-right: none;
  background: transparent;

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    color: #bfcbd9;

    &:hover {
      background: #263445;
    }

    &.is-active {
      color: #409eff;
      background: #1f2d3d;
    }
  }
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  padding: 0 16px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
    }

    .breadcrumb {
      line-height: 60px;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-search {
      width: 200px;
    }

    .header-icon {
      font-size: 20px;
      cursor: pointer;
      color: #606266;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;

      .username {
        font-size: 14px;
      }
    }
  }
}

.content {
  background: #f0f2f5;
  padding: 16px;
  overflow-y: auto;
}
</style>
