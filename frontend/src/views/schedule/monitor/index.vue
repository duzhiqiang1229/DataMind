<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>任务监控</span>
        <div>
          <el-button type="primary" :icon="Promotion" @click="openAirflowNewWindow">打开 Airflow 界面</el-button>
          <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
        </div>
      </div>
    </template>

    <div class="search-bar">
      <el-select v-model="searchDag" placeholder="DAG 名称" clearable filterable style="width: 220px;" @change="handleSearch">
        <el-option v-for="d in dagOptions" :key="d" :label="d" :value="d" />
      </el-select>
      <el-select v-model="searchStatus" placeholder="状态" clearable style="width: 120px;" @change="handleSearch">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
        <el-option label="运行中" value="running" />
        <el-option label="排队" value="queued" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>

    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="dag_id" label="DAG 名称" width="220" show-overflow-tooltip />
      <el-table-column label="Run ID" min-width="200">
        <template #default="{ row }">
          <el-tooltip :content="row.dag_run_id || '-'" placement="top">
            <span class="mono-text run-id">{{ formatRunId(row.dag_run_id, row.start_date) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="触发" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.run_type || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="state" label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.state)">{{ row.state }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开始" width="180">
        <template #default="{ row }">{{ formatDateTime(row.start_date) }}</template>
      </el-table-column>
      <el-table-column label="结束" width="180">
        <template #default="{ row }">{{ formatDateTime(row.end_date) }}</template>
      </el-table-column>
      <el-table-column label="时长" width="110" align="center">
        <template #default="{ row }">{{ formatDuration(row.start_date, row.end_date) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.page_size"
      :total="pagination.total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="loadData"
      @size-change="loadData"
      style="margin-top: 16px; justify-content: flex-end;"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Refresh, RefreshLeft, Promotion } from "@element-plus/icons-vue";
import { airflowApi } from "@/api";
import { formatDateTime, formatRunId } from "@/utils/format";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const airflowUrl = "http://192.168.1.4:8082/home";

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const searchDag = ref("");
const searchStatus = ref("");
const dagOptions = ref<string[]>([]);

function openAirflowNewWindow() {
  window.open(airflowUrl, "_blank", "noopener,noreferrer");
}

async function loadData() {
  loading.value = true;
  try {
    const res = await airflowApi.dagRuns({
      page: pagination.page,
      page_size: pagination.page_size,
      dag_id: searchDag.value || undefined,
      status: searchStatus.value || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
    // collect distinct dag ids for the filter
    const dags = new Set<string>();
    (res.items || []).forEach((r: any) => r.dag_id && dags.add(r.dag_id));
    dagOptions.value = [...dags];
  } catch {
    tableData.value = [];
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.page = 1;
  loadData();
}

function handleReset() {
  searchDag.value = "";
  searchStatus.value = "";
  pagination.page = 1;
  loadData();
}

function statusTag(status: string): TagType {
  const map: Record<string, TagType> = {
    success: "success",
    failed: "danger",
    running: "warning",
    queued: "info",
    skipped: "info",
    upstream_failed: "danger",
  };
  return map[status] || "info";
}

function formatDuration(start?: string, end?: string): string {
  if (!start || !end) return "-";
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  if (isNaN(s) || isNaN(e) || e < s) return "-";
  const seconds = Math.floor((e - s) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remSec = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remSec}s`;
  const hours = Math.floor(minutes / 60);
  const remMin = minutes % 60;
  return `${hours}h ${remMin}m`;
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
