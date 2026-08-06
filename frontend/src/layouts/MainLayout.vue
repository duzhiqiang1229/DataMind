<template>
  <el-container class="main-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '210px'" class="sidebar">
      <div class="logo">
        <el-icon size="28"><DataLine /></el-icon>
        <span v-show="!isCollapse" class="logo-text">DataMind</span>
      </div>
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>首页驾驶舱</span>
        </el-menu-item>
        <el-menu-item index="/datasource">
          <el-icon><Coin /></el-icon>
          <span>数据源管理</span>
        </el-menu-item>
        <el-menu-item index="/datax">
          <el-icon><Sort /></el-icon>
          <span>DataX 同步</span>
        </el-menu-item>
        <el-menu-item index="/spark">
          <el-icon><Cpu /></el-icon>
          <span>Spark 任务</span>
        </el-menu-item>
        <el-menu-item index="/query">
          <el-icon><Monitor /></el-icon>
          <span>SQL 工作台</span>
        </el-menu-item>
        <el-menu-item index="/data-model">
          <el-icon><Files /></el-icon>
          <span>数据模型</span>
        </el-menu-item>
        <el-menu-item index="/publish">
          <el-icon><Promotion /></el-icon>
          <span>发布管理</span>
        </el-menu-item>
        <el-menu-item index="/warehouse/browse">
          <el-icon><FolderOpened /></el-icon>
          <span>库表浏览</span>
        </el-menu-item>
        <el-menu-item index="/metrics">
          <el-icon><DataAnalysis /></el-icon>
          <span>指标中心</span>
        </el-menu-item>
        <el-menu-item index="/assets/catalog">
          <el-icon><Collection /></el-icon>
          <span>数据目录</span>
        </el-menu-item>
        <el-menu-item index="/schedule/monitor">
          <el-icon><Timer /></el-icon>
          <span>任务监控</span>
        </el-menu-item>
        <el-sub-menu index="/system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/system/user">用户管理</el-menu-item>
          <el-menu-item index="/system/role">角色管理</el-menu-item>
          <el-menu-item index="/system/component">组件配置</el-menu-item>
          <el-menu-item index="/system/config">系统配置</el-menu-item>
          <el-menu-item index="/system/log">操作日志</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <!-- Main content -->
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" :src="authStore.userInfo?.avatar || undefined" />
              <span class="username">{{ authStore.userInfo?.full_name || authStore.userInfo?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
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
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const isCollapse = ref(false);

async function handleLogout() {
  try {
    await authStore.logout();
    router.push("/login");
  } catch {
    // ignore
  }
}
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

  .collapse-btn {
    font-size: 20px;
    cursor: pointer;
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

.content {
  background: #f0f2f5;
  padding: 16px;
  overflow-y: auto;
}
</style>
