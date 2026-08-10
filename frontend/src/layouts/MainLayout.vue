<template>
  <el-container class="main-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <div class="logo-icon">
          <el-icon size="22"><DataLine /></el-icon>
        </div>
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
          </el-sub-menu>

          <!-- 数据建模 -->
          <el-sub-menu index="/data-modeling">
            <template #title>
              <el-icon><Files /></el-icon>
              <span>数据建模</span>
            </template>
            <el-menu-item index="/data-modeling/domain">数据域</el-menu-item>
            <el-menu-item index="/data-modeling/process">业务过程</el-menu-item>
            <el-menu-item index="/data-modeling/model">模型设计</el-menu-item>
          </el-sub-menu>

          <!-- 数据开发 -->
          <el-sub-menu index="/dev">
            <template #title>
              <el-icon><EditPen /></el-icon>
              <span>数据开发</span>
            </template>
            <el-menu-item index="/datax">数据集成</el-menu-item>
            <el-menu-item index="/query">ETL 开发</el-menu-item>
          </el-sub-menu>

          <!-- 调度中心 -->
          <el-sub-menu index="/schedule">
            <template #title>
              <el-icon><Timer /></el-icon>
              <span>调度中心</span>
            </template>
            <el-menu-item index="/schedule/monitor">任务监控</el-menu-item>
            <el-menu-item index="/schedule/task">调度任务</el-menu-item>
          </el-sub-menu>

          <!-- 数据资产 -->
          <el-sub-menu index="/assets">
            <template #title>
              <el-icon><Collection /></el-icon>
              <span>数据资产</span>
            </template>
            <el-menu-item index="/assets/catalog">数据目录</el-menu-item>
            <el-menu-item index="/assets/lineage">血缘关系</el-menu-item>
            <el-menu-item index="/assets/steward">数据责任人</el-menu-item>
          </el-sub-menu>

          <!-- 指标中心 -->
          <el-sub-menu index="/metrics">
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>指标中心</span>
            </template>
            <el-menu-item index="/metrics/modeling">Cube 建模</el-menu-item>
            <el-menu-item index="/metrics/definitions">指标定义</el-menu-item>
            <el-menu-item index="/metrics/query">指标查询</el-menu-item>
          </el-sub-menu>

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
            <el-menu-item index="/system/component">组件配置</el-menu-item>
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
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索功能..."
            :prefix-icon="Search"
            size="small"
            class="header-search"
            @keyup.enter="handleSearch"
          />
          <el-tooltip content="组件连接状态" placement="bottom">
            <el-badge :value="componentIssues" :hidden="componentIssues === 0" type="danger">
              <el-icon class="header-icon" @click="router.push('/system/component')"><Connection /></el-icon>
            </el-badge>
          </el-tooltip>
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
    "sql": "/query", "查询": "/query", "工作台": "/query",
    "模型": "/data-modeling/model", "发布": "/publish", "监控": "/schedule/monitor", "调度": "/schedule/monitor",
    "目录": "/assets/catalog", "血缘": "/assets/lineage",
    "指标": "/metrics/definitions", "服务": "/data-service", "用户": "/system/user",
    "角色": "/system/role", "组件": "/system/component", "首页": "/dashboard",
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
  background: #1e293b;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  background: rgba(0, 0, 0, 0.2);

  .logo-icon {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: linear-gradient(135deg, #4366e5, #6c8aff);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(67, 102, 229, 0.4);
  }

  .logo-text {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    white-space: nowrap;
    letter-spacing: 0.5px;
  }
}

.sidebar-scroll {
  height: calc(100vh - 60px);
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  padding: 8px 0;

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    color: #94a3b8;
    height: 44px;
    line-height: 44px;
    margin: 2px 8px;
    border-radius: 6px;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #e2e8f0;
    }

    &.is-active {
      background: linear-gradient(135deg, rgba(67, 102, 229, 0.3), rgba(67, 102, 229, 0.1));
      color: #fff;
      box-shadow: inset 3px 0 0 #4366e5;
    }
  }

  :deep(.el-sub-menu .el-menu-item) {
    height: 40px;
    line-height: 40px;
    font-size: 13px;
    min-width: auto;
  }

  :deep(.el-sub-menu .el-menu) {
    background: rgba(0, 0, 0, 0.15);
    border-radius: 6px;
    margin: 2px 0;
  }
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  padding: 0 20px;
  height: 56px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      font-size: 18px;
      cursor: pointer;
      color: #64748b;
      transition: color 0.2s;

      &:hover {
        color: #4366e5;
      }
    }

    .breadcrumb {
      line-height: 56px;

      :deep(.el-breadcrumb__item) {
        .el-breadcrumb__inner {
          color: #94a3b8;
          font-size: 13px;
        }

        &:last-child .el-breadcrumb__inner {
          color: #1e293b;
          font-weight: 600;
        }
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-search {
      width: 200px;

      :deep(.el-input__wrapper) {
        background: #f1f5f9;
        box-shadow: none;
        border-radius: 20px;

        &:hover {
          background: #e2e8f0;
        }

        &.is-focus {
          background: #fff;
          box-shadow: 0 0 0 2px #4366e5;
        }
      }
    }

    .header-icon {
      font-size: 20px;
      cursor: pointer;
      color: #64748b;
      transition: color 0.2s;

      &:hover {
        color: #4366e5;
      }
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 8px;
      transition: background 0.2s;

      &:hover {
        background: #f1f5f9;
      }

      .username {
        font-size: 14px;
        color: #1e293b;
        font-weight: 500;
      }
    }
  }
}

.content {
  background: #f8fafc;
  padding: 20px;
  overflow-y: auto;
}
</style>
