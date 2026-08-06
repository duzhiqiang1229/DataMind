<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据源管理</span>
          <el-button type="primary" :icon="Plus">新增数据源</el-button>
        </div>
      </template>

      <el-form :inline="true" class="search-form">
        <el-form-item label="类型">
          <el-select v-model="search.type" placeholder="全部" clearable style="width: 120px;">
            <el-option label="MySQL" value="mysql" />
            <el-option label="Oracle" value="oracle" />
            <el-option label="PostgreSQL" value="postgresql" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" border>
        <el-table-column prop="source_name" label="名称" />
        <el-table-column prop="source_type" label="类型" width="100" />
        <el-table-column prop="host" label="地址" />
        <el-table-column prop="database_name" label="数据库" width="120" />
        <el-table-column label="连接状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.last_connection_ok ? 'success' : 'danger'" size="small">
              {{ row.last_connection_ok ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleTest(row)">测试</el-button>
            <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { datasourceApi } from "@/api";

const loading = ref(false);
const tableData = ref([]);
const search = ref({ type: "" });
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

async function loadData() {
  loading.value = true;
  try {
    const res = await datasourceApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      source_type: search.value.type || undefined,
    });
    tableData.value = res.items;
    pagination.total = res.total;
  } finally {
    loading.value = false;
  }
}

async function handleTest(row: any) {
  try {
    const res = await datasourceApi.testConnection(row.id);
    ElMessage.success(`连接成功 (${res.version || "OK"})`);
    loadData();
  } catch {
    // handled by interceptor
  }
}

function handleEdit(row: any) {
  // TODO: open edit dialog
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除数据源 "${row.source_name}"?`, "提示", { type: "warning" });
  await datasourceApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-form {
  margin-bottom: 16px;
}
</style>
