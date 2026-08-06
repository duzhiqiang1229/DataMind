<template>
  <el-card>
    <template #header>操作日志</template>
    <el-form :inline="true" class="search-form">
      <el-form-item label="模块">
        <el-select v-model="searchModule" placeholder="全部" clearable style="width: 150px;" @change="loadData">
          <el-option label="认证" value="auth" />
          <el-option label="用户" value="user" />
          <el-option label="数据源" value="datasource" />
          <el-option label="DataX" value="datax" />
          <el-option label="Doris查询" value="doris" />
          <el-option label="系统" value="system" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="username" label="用户" width="100" />
      <el-table-column prop="module" label="模块" width="100" />
      <el-table-column prop="action" label="操作" width="100" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="request_method" label="方法" width="80" />
      <el-table-column prop="status_code" label="状态码" width="80" />
      <el-table-column prop="ip_address" label="IP" width="120" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>

    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.page_size"
      :total="pagination.total"
      layout="total, prev, pager, next, jumper"
      @current-change="loadData"
      style="margin-top: 16px; justify-content: flex-end;"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { systemApi } from "@/api";

const loading = ref(false);
const tableData = ref<any[]>([]);
const searchModule = ref("");
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

async function loadData() {
  loading.value = true;
  try {
    const res = await systemApi.logs({
      page: pagination.page,
      page_size: pagination.page_size,
      module: searchModule.value || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.search-form { margin-bottom: 16px; }
</style>
