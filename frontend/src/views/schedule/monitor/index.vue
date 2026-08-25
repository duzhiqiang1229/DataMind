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
      <el-table-column label="任务" width="80" align="right"><template #default="{ row }">{{ row.task_count || 0 }}</template></el-table-column>
      <el-table-column label="输入/输出" width="110" align="center"><template #default="{ row }">{{ row.input_asset_count || 0 }} / {{ row.output_asset_count || 0 }}</template></el-table-column>
      <el-table-column label="运行血缘" width="105" align="center">
        <template #default="{ row }"><el-tag size="small" :type="lineageTag(row.lineage_status)">{{ lineageLabel(row.lineage_status) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }"><el-button link type="primary" @click="openTasks(row)">任务明细</el-button></template>
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

    <el-drawer v-model="taskDrawer" title="任务执行流" size="min(1180px, 94vw)">
      <div v-loading="taskLoading" class="task-visual">
        <el-empty v-if="!taskLoading && !taskRows.length" description="该运行尚未收到任务回调" />
        <template v-else-if="currentRun">
          <div class="run-overview">
            <div class="run-identity">
              <span class="overview-label">DAG 运行</span>
              <strong>{{ currentRun.dag_id }}</strong>
              <span class="mono-text">{{ formatRunId(currentRun.dag_run_id, currentRun.start_date) }}</span>
            </div>
            <div class="overview-stat"><span>状态</span><el-tag :type="statusTag(currentRun.state)">{{ currentRun.state }}</el-tag></div>
            <div class="overview-stat"><span>任务数</span><strong>{{ taskRows.length }}</strong></div>
            <div class="overview-stat success"><span>成功</span><strong>{{ taskStateCount.success }}</strong></div>
            <div class="overview-stat failed"><span>失败</span><strong>{{ taskStateCount.failed }}</strong></div>
            <div class="overview-stat"><span>总时长</span><strong>{{ formatDuration(currentRun.start_date, currentRun.end_date) }}</strong></div>
          </div>

          <div class="flow-heading">
            <div><strong>执行流</strong><span>按任务实际开始时间分层，同层任务为并行执行</span></div>
            <div class="flow-legend"><i class="success"></i>成功<i class="running"></i>运行中<i class="failed"></i>失败<i class="waiting"></i>等待</div>
          </div>

          <div class="flow-canvas">
            <template v-for="(stage, stageIndex) in taskStages" :key="stageIndex">
              <section class="flow-stage">
                <div class="stage-title"><span>阶段 {{ stageIndex + 1 }}</span><small>{{ stage.length }} 个任务</small></div>
                <button
                  v-for="task in stage"
                  :key="task.id"
                  type="button"
                  class="task-node"
                  :class="[task.state, { active: selectedTask?.id === task.id }]"
                  @click="selectedTask = task"
                >
                  <span class="status-icon">
                    <el-icon v-if="task.state === 'success'"><CircleCheck /></el-icon>
                    <el-icon v-else-if="task.state === 'failed' || task.state === 'upstream_failed'"><CircleClose /></el-icon>
                    <el-icon v-else-if="task.state === 'running'" class="is-loading"><Loading /></el-icon>
                    <el-icon v-else><Clock /></el-icon>
                  </span>
                  <span class="node-content">
                    <strong>{{ task.task_id }}</strong>
                    <small>{{ task.operator_type || "未知算子" }}</small>
                    <span class="node-meta"><em>{{ task.duration_seconds == null ? "--" : `${task.duration_seconds}s` }}</em><em>{{ (task.input_tables || []).length }} 入 / {{ (task.output_tables || []).length }} 出</em></span>
                  </span>
                </button>
              </section>
              <div v-if="stageIndex < taskStages.length - 1" class="stage-arrow"><span></span><el-icon><ArrowRight /></el-icon></div>
            </template>
          </div>

          <el-card v-if="selectedTask" shadow="never" class="selected-detail">
            <template #header>
              <div class="detail-title">
                <div><span>节点详情</span><strong>{{ selectedTask.task_id }}</strong></div>
                <el-tag :type="statusTag(selectedTask.state)">{{ selectedTask.state }}</el-tag>
              </div>
            </template>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="算子">{{ selectedTask.operator_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="尝试次数">{{ selectedTask.try_number }}</el-descriptions-item>
              <el-descriptions-item label="执行时长">{{ selectedTask.duration_seconds == null ? '-' : `${selectedTask.duration_seconds}s` }}</el-descriptions-item>
              <el-descriptions-item label="开始时间">{{ formatDateTime(selectedTask.start_date) }}</el-descriptions-item>
              <el-descriptions-item label="结束时间">{{ formatDateTime(selectedTask.end_date) }}</el-descriptions-item>
              <el-descriptions-item label="影响行数">{{ selectedTask.affected_rows ?? '-' }}</el-descriptions-item>
              <el-descriptions-item label="输入表" :span="3"><div class="asset-tags"><el-tag v-for="table in selectedTask.input_tables || []" :key="table" size="small" effect="plain">{{ table }}</el-tag><span v-if="!selectedTask.input_tables?.length">-</span></div></el-descriptions-item>
              <el-descriptions-item label="输出表" :span="3"><div class="asset-tags"><el-tag v-for="table in selectedTask.output_tables || []" :key="table" size="small" type="success" effect="plain">{{ table }}</el-tag><span v-if="!selectedTask.output_tables?.length">-</span></div></el-descriptions-item>
              <el-descriptions-item v-if="selectedTask.error_message" label="错误信息" :span="3"><div class="error-message">{{ selectedTask.error_message }}</div></el-descriptions-item>
            </el-descriptions>
          </el-card>
        </template>
      </div>
    </el-drawer>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from "vue";
import { ArrowRight, CircleCheck, CircleClose, Clock, Loading, Promotion, Refresh } from "@element-plus/icons-vue";
import { airflowApi } from "@/api";
import { formatDateTime, formatRunId } from "@/utils/format";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const airflowUrl = import.meta.env.VITE_AIRFLOW_URL
  || `${window.location.protocol}//${window.location.hostname}:8082`;

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const searchDag = ref("");
const searchStatus = ref("");
const dagOptions = ref<string[]>([]);
const taskDrawer = ref(false);
const taskLoading = ref(false);
const taskRows = ref<any[]>([]);
const currentRun = ref<any>();
const selectedTask = ref<any>();
const taskStateCount = computed(() => taskRows.value.reduce((result, task) => {
  if (task.state === "success") result.success += 1;
  if (task.state === "failed" || task.state === "upstream_failed") result.failed += 1;
  return result;
}, { success: 0, failed: 0 }));
const taskStages = computed(() => {
  const tasks = [...taskRows.value].sort((a, b) => {
    const left = a.start_date ? new Date(a.start_date).getTime() : Number.MAX_SAFE_INTEGER;
    const right = b.start_date ? new Date(b.start_date).getTime() : Number.MAX_SAFE_INTEGER;
    return left - right || String(a.task_id).localeCompare(String(b.task_id));
  });
  const stages: any[][] = [];
  let stageAnchor: number | undefined;
  tasks.forEach((task) => {
    const startedAt = task.start_date ? new Date(task.start_date).getTime() : undefined;
    if (!stages.length || stageAnchor === undefined || startedAt === undefined || startedAt - stageAnchor > 1500) {
      stages.push([task]);
      stageAnchor = startedAt;
    } else {
      stages[stages.length - 1].push(task);
    }
  });
  return stages;
});

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

async function openTasks(row: any) {
  taskDrawer.value = true;
  taskLoading.value = true;
  taskRows.value = [];
  currentRun.value = row;
  selectedTask.value = undefined;
  try { taskRows.value = (await airflowApi.dagRunTasks(row.id)) || []; selectedTask.value = taskRows.value[0]; }
  finally { taskLoading.value = false; }
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

function lineageTag(status: string): TagType {
  return status === "collected" ? "success" : status === "partial" ? "warning" : "info";
}

function lineageLabel(status: string): string {
  return ({ collected: "已采集", partial: "部分匹配", none: "无血缘", pending: "待采集" } as any)[status] || "待采集";
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
.task-visual { min-height:420px; }
.run-overview { display:grid; grid-template-columns:minmax(240px,1.7fr) repeat(5,minmax(90px,.6fr)); gap:10px; padding:14px; border:1px solid var(--el-border-color-lighter); border-radius:10px; background:linear-gradient(135deg,#f8fafc,#f1f5f9); }
.run-identity { display:flex; min-width:0; flex-direction:column; gap:4px; padding-right:12px; border-right:1px solid var(--el-border-color-lighter); }
.run-identity strong { overflow:hidden; font-size:15px; text-overflow:ellipsis; white-space:nowrap; }
.run-identity .mono-text { overflow:hidden; color:var(--el-text-color-secondary); font-size:11px; text-overflow:ellipsis; white-space:nowrap; }
.overview-label,.overview-stat span { color:var(--el-text-color-secondary); font-size:11px; }
.overview-stat { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px; }
.overview-stat strong { font-size:17px; }
.overview-stat.success strong { color:var(--el-color-success); }
.overview-stat.failed strong { color:var(--el-color-danger); }
.flow-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; margin:22px 0 12px; }
.flow-heading > div:first-child { display:flex; align-items:baseline; gap:10px; }
.flow-heading span { color:var(--el-text-color-secondary); font-size:12px; }
.flow-legend { display:flex; align-items:center; gap:6px; color:var(--el-text-color-secondary); font-size:11px; }
.flow-legend i { width:8px; height:8px; margin-left:5px; border-radius:50%; background:#94a3b8; }
.flow-legend i.success { background:#22c55e; }.flow-legend i.running { background:#f59e0b; }.flow-legend i.failed { background:#ef4444; }
.flow-canvas { display:flex; align-items:center; min-height:250px; padding:20px; overflow:auto; border:1px solid #dbe4ef; border-radius:10px; background-color:#f8fafc; background-image:radial-gradient(#cbd5e1 1px,transparent 1px); background-size:18px 18px; }
.flow-stage { display:flex; min-width:210px; flex-direction:column; align-self:stretch; justify-content:center; gap:10px; }
.stage-title { display:flex; align-items:center; justify-content:space-between; padding:0 4px; color:#475569; font-size:12px; }
.stage-title small { color:#94a3b8; }
.stage-arrow { display:flex; flex:0 0 72px; align-items:center; color:#94a3b8; }
.stage-arrow span { height:2px; flex:1; background:#cbd5e1; }
.stage-arrow .el-icon { margin-left:-2px; font-size:18px; }
.task-node { display:flex; width:210px; align-items:flex-start; gap:10px; padding:12px; border:1px solid #dbe4ef; border-left:4px solid #94a3b8; border-radius:8px; background:#fff; color:inherit; text-align:left; cursor:pointer; box-shadow:0 2px 6px rgba(15,23,42,.05); transition:.18s ease; }
.task-node:hover,.task-node.active { border-color:var(--el-color-primary-light-5); border-left-color:var(--el-color-primary); box-shadow:0 5px 16px rgba(37,99,235,.14); transform:translateY(-1px); }
.task-node.success { border-left-color:#22c55e; }.task-node.failed,.task-node.upstream_failed { border-left-color:#ef4444; }.task-node.running { border-left-color:#f59e0b; }
.status-icon { display:grid; flex:0 0 28px; height:28px; place-items:center; border-radius:50%; background:#f1f5f9; color:#64748b; font-size:18px; }
.task-node.success .status-icon { background:#ecfdf5; color:#16a34a; }.task-node.failed .status-icon,.task-node.upstream_failed .status-icon { background:#fef2f2; color:#dc2626; }.task-node.running .status-icon { background:#fffbeb; color:#d97706; }
.node-content { display:flex; min-width:0; flex:1; flex-direction:column; gap:4px; }
.node-content strong,.node-content small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.node-content strong { font-size:13px; }.node-content small { color:var(--el-text-color-secondary); font-size:10px; }
.node-meta { display:flex; justify-content:space-between; gap:8px; margin-top:3px; color:#64748b; font-size:10px; }
.node-meta em { font-style:normal; }
.selected-detail { margin-top:16px; }
.detail-title { display:flex; align-items:center; justify-content:space-between; }
.detail-title > div { display:flex; align-items:center; gap:12px; }.detail-title span { color:var(--el-text-color-secondary); font-size:12px; }
.asset-tags { display:flex; flex-wrap:wrap; gap:6px; }
.error-message { color:var(--el-color-danger); white-space:pre-wrap; }
@media(max-width:900px){.run-overview{grid-template-columns:1fr 1fr 1fr}.run-identity{grid-column:1/-1;border-right:0;border-bottom:1px solid var(--el-border-color-lighter);padding-bottom:10px}.flow-heading{align-items:flex-start;flex-direction:column}.selected-detail :deep(.el-descriptions__body .el-descriptions__table){min-width:720px}}
</style>
