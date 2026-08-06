<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>用户管理</span>
        <el-button type="primary" :icon="Plus">新增用户</el-button>
      </div>
    </template>
    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="full_name" label="姓名" width="100" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="department" label="部门" width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" width="180" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary">编辑</el-button>
          <el-button text type="primary">重置密码</el-button>
          <el-button text type="warning">{{ row.status === 'active' ? '禁用' : '启用' }}</el-button>
          <el-button text type="primary">分配角色</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";

const loading = ref(false);
const tableData = ref([]);

onMounted(async () => {
  // TODO: load users
});
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
