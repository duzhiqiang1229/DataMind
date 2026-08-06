<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>任务监控</span>
        <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
      </div>
    </template>

    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="6" v-for="stat in statCards" :key="stat.label">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon :size="28" :color="stat.color"><component :is="stat.icon" /></el-icon>
            <div>
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-form :inline="true" class="search-form">
      <el-form-item label="类型">
        <el-select v-model="searchType" placeholder="全部" clearable style="width: 120px;" @change="loadData">
          <el-option label="DataX" value="datax" />
          <el-option label="Spark" value="spark" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="searchStatus" placeholder="全部" clearable style="width: 120px;" @change="loadData">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="运行中" value="running" />
          <el-option label="排队" value="queued" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="task_type" label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.task_type === 'spark' ? 'warning' : 'info'">{{ row.task_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="dag_run_id" label="执行ID" width="200" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="started_at" label="开始时间" width="180" />
      <el-table-column prop="ended_at" label="结束时间" width="180" />
      <el-table-column prop="duration_seconds" label="耗时(秒)" width="100" />
      <el-table-column prop="rows_read" label="读取行数" width="100" />
      <el-table-column prop="rows_written" label="写入行数" width="100" />
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
import { Refresh } from "@element-plus/icons-vue";
import request from "@/api/request";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const loading = ref(false);
const tableData = ref<any[]>([]);
const searchType = ref("");
const searchStatus = ref("");
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const statCards = ref([
  { label: "总执行", value: 0, icon: "List", color: "#409eff" },
  { label: "成功", value: 0, icon: "CircleCheck", color: "#67c23a" },
  { label: "失败", value: 0, icon: "CircleClose", color: "#f56c6c" },
  { label: "运行中", value: 0, icon: "Loading", color: "#e6a23c" },
]);

async function loadData() {
  loading.value = true;
  try {
    // Use dashboard stats for overview counts
    const stats = await request.get("/dashboard/stats");
    statCards.value[0].value = stats.today_executions || 0;
    // Load recent tasks as the table data
    const tasks = await request.get("/dashboard/recent-tasks", { params: { limit: 50 } });
    let data = tasks || [];
    if (searchType.value) data = data.filter((t: any) => t.task_type === searchType.value);
    if (searchStatus.value) data = data.filter((t: any) => t.status === searchStatus.value);
    tableData.value = data;
    pagination.total = data.length;
    // Update stat cards
    statCards.value[1].value = data.filter((t: any) => t.status === "success").length;
    statCards.value[2].value = data.filter((t: any) => t.status === "failed").length;
    statCards.value[3].value = data.filter((t: any) => t.status === "running").length;
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

function statusTag(status: string): TagType {
  const map: Record<string, TagType> = { success: "success", failed: "danger", running: "warning", queued: "info" };
  return map[status] || "info";
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.search-form { margin-bottom: 12px; }
.stat-card { display: flex; align-items: center; gap: 12px; }
.stat-value { font-size: 22px; font-weight: bold; color: #303133; }
.stat-label { font-size: 13px; color: #909399; }
</style>
