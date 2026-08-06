<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>DataX 同步任务</span>
          <el-button type="primary" :icon="Plus">新建同步任务</el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" border>
        <el-table-column prop="task_name" label="任务名称" />
        <el-table-column prop="task_code" label="编码" width="150" />
        <el-table-column prop="source_table" label="源表" width="120" />
        <el-table-column prop="target_table" label="目标表" width="120" />
        <el-table-column prop="sync_mode" label="模式" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.sync_mode === 'incremental' ? 'warning' : 'info'">
              {{ row.sync_mode === 'incremental' ? '增量' : '全量' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleTrigger(row)">执行</el-button>
            <el-button text type="primary" @click="handleHistory(row)">历史</el-button>
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
import { dataxApi } from "@/api";

const loading = ref(false);
const tableData = ref([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

async function loadData() {
  loading.value = true;
  try {
    const res = await dataxApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
    });
    tableData.value = res.items;
    pagination.total = res.total;
  } finally {
    loading.value = false;
  }
}

async function handleTrigger(row: any) {
  await ElMessageBox.confirm(`确认立即执行任务 "${row.task_name}"?`, "执行确认");
  try {
    const res = await dataxApi.trigger(row.id);
    ElMessage.success(`任务已触发，执行ID: ${res.dag_run_id}`);
  } catch {
    // handled
  }
}

function handleHistory(row: any) {
  // TODO: open history drawer
}

function handleEdit(row: any) {
  // TODO: open edit dialog
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除任务 "${row.task_name}"?`, "提示", { type: "warning" });
  await dataxApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function statusTag(status: string) {
  return { draft: "info", active: "success", paused: "warning", archived: "info" }[status] || "info";
}

function statusLabel(status: string) {
  return { draft: "草稿", active: "启用", paused: "暂停", archived: "归档" }[status] || status;
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
