<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>DAG 管理</span>
        <el-button :icon="Refresh" @click="loadDags" :loading="loading">刷新</el-button>
      </div>
    </template>

    <el-alert
      v-if="showNotConfigured"
      title="Airflow 未配置或不可用，请先在系统组件管理中配置 Airflow 连接。"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    />

    <el-table :data="dagList" v-loading="loading" border style="width: 100%;">
      <el-table-column prop="dag_id" label="DAG ID" min-width="220" show-overflow-tooltip />
      <el-table-column prop="schedule_interval" label="调度周期" width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.schedule_interval ?? row.schedule_interval_value ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.is_paused ? 'warning' : 'success'" size="small">
            {{ row.is_paused ? '暂停' : '运行中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="负责人" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ formatOwners(row.owners) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="标签" min-width="180">
        <template #default="{ row }">
          <el-tag
            v-for="tag in row.tags || []"
            :key="typeof tag === 'string' ? tag : tag.name"
            size="small"
            type="info"
            style="margin-right: 4px; margin-bottom: 2px;"
          >
            {{ typeof tag === 'string' ? tag : tag.name }}
          </el-tag>
          <span v-if="!row.tags || row.tags.length === 0">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button
            size="small"
            :type="row.is_paused ? 'success' : 'warning'"
            link
            @click="togglePause(row)"
          >
            {{ row.is_paused ? '恢复' : '暂停' }}
          </el-button>
          <el-button size="small" type="primary" link @click="confirmTrigger(row)">触发</el-button>
          <el-button size="small" type="info" link @click="openHistory(row)">运行历史</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 运行历史 Drawer -->
    <el-drawer
      v-model="historyDrawer"
      :title="`运行历史 - ${currentDag?.dag_id ?? ''}`"
      size="70%"
      direction="rtl"
      destroy-on-close
    >
      <div v-loading="runsLoading">
        <el-table :data="dagRuns" border size="small">
          <el-table-column prop="dag_run_id" label="Run ID" min-width="220" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="runStateTag(row.state)" size="small">{{ row.state || '未知' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_date" label="开始时间" width="180" show-overflow-tooltip />
          <el-table-column prop="end_date" label="结束时间" width="180" show-overflow-tooltip />
          <el-table-column label="耗时" width="120">
            <template #default="{ row }">
              {{ formatDuration(row.start_date, row.end_date) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openRunDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!runsLoading && dagRuns.length === 0" style="text-align: center; padding: 20px; color: #909399;">
          暂无运行记录
        </div>
      </div>
    </el-drawer>

    <!-- 运行详情 Dialog (task instances + log) -->
    <el-dialog
      v-model="runDetailDialog"
      :title="`运行详情 - ${currentRun?.dag_run_id ?? ''}`"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <div v-loading="runDetailLoading">
        <el-descriptions :column="3" border size="small" style="margin-bottom: 16px;">
          <el-descriptions-item label="Run ID">{{ currentRun?.dag_run_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="runStateTag(currentRun?.state)" size="small">{{ currentRun?.state || '未知' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ currentRun?.start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ currentRun?.end_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ formatDuration(currentRun?.start_date, currentRun?.end_date) }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 12px 0 8px;">任务实例</h4>
        <el-table :data="taskInstances" border size="small">
          <el-table-column prop="task_id" label="Task ID" min-width="180" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="runStateTag(row.state)" size="small">{{ row.state || '未知' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="try_number" label="尝试次数" width="100" />
          <el-table-column prop="start_date" label="开始时间" width="180" show-overflow-tooltip />
          <el-table-column prop="end_date" label="结束时间" width="180" show-overflow-tooltip />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openLog(row)">日志</el-button>
              <el-button
                v-if="isFailedState(row.state)"
                size="small"
                type="warning"
                link
                @click="retryTask(row)"
              >
                重试
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!runDetailLoading && taskInstances.length === 0" style="text-align: center; padding: 20px; color: #909399;">
          暂无任务实例
        </div>
      </div>
    </el-dialog>

    <!-- 日志查看 Dialog -->
    <el-dialog
      v-model="logDialog"
      :title="`日志 - ${currentTask?.task_id ?? ''}`"
      width="75%"
      top="5vh"
      destroy-on-close
      append-to-body
    >
      <div v-loading="logLoading">
        <div style="margin-bottom: 8px;">
          <el-button size="small" @click="loadLog(currentTask, 1)" :loading="logLoading">刷新日志</el-button>
        </div>
        <pre class="log-pre">{{ logContent || '暂无日志' }}</pre>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { airflowApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const loading = ref(false);
const dagList = ref<any[]>([]);
const showNotConfigured = ref(false);

// history drawer
const historyDrawer = ref(false);
const currentDag = ref<any>(null);
const dagRuns = ref<any[]>([]);
const runsLoading = ref(false);

// run detail dialog
const runDetailDialog = ref(false);
const currentRun = ref<any>(null);
const taskInstances = ref<any[]>([]);
const runDetailLoading = ref(false);

// log dialog
const logDialog = ref(false);
const currentTask = ref<any>(null);
const logContent = ref("");
const logLoading = ref(false);

onMounted(loadDags);

async function loadDags() {
  loading.value = true;
  showNotConfigured.value = false;
  try {
    const res = await airflowApi.listDags();
    const list = Array.isArray(res) ? res : res?.items || res?.dags || [];
    dagList.value = list;
    if (list.length === 0) {
      showNotConfigured.value = true;
    }
  } catch (e: any) {
    showNotConfigured.value = true;
    dagList.value = [];
  } finally {
    loading.value = false;
  }
}

function formatOwners(owners: any): string {
  if (!owners) return "-";
  if (Array.isArray(owners)) return owners.join(", ");
  return String(owners);
}

async function togglePause(row: any) {
  const action = row.is_paused ? "恢复" : "暂停";
  try {
    await ElMessageBox.confirm(`确定要${action} DAG "${row.dag_id}" 吗？`, "提示", {
      type: "warning",
    });
    if (row.is_paused) {
      await airflowApi.resumeDag(row.dag_id);
    } else {
      await airflowApi.pauseDag(row.dag_id);
    }
    ElMessage.success(`${action}成功`);
    row.is_paused = !row.is_paused;
  } catch (e: any) {
    if (e !== "cancel" && e?.message !== "cancel") {
      ElMessage.error(`${action}失败: ${e?.message || e}`);
    }
  }
}

async function confirmTrigger(row: any) {
  try {
    const { value } = await ElMessageBox.prompt(
      `确定要触发 DAG "${row.dag_id}" 运行吗？可传入运行参数(JSON)。`,
      "触发确认",
      {
        confirmButtonText: "触发",
        cancelButtonText: "取消",
        inputType: "textarea",
        inputPlaceholder: '{"key": "value"}  (可选)',
        inputValue: "",
      }
    );
    let conf: any = {};
    if (value && value.trim()) {
      try {
        conf = JSON.parse(value);
      } catch {
        ElMessage.error("参数不是合法的 JSON");
        return;
      }
    }
    await airflowApi.triggerDag(row.dag_id, conf);
    ElMessage.success("触发成功");
  } catch (e: any) {
    if (e !== "cancel" && e?.message !== "cancel") {
      ElMessage.error(`触发失败: ${e?.message || e}`);
    }
  }
}

async function openHistory(row: any) {
  currentDag.value = row;
  historyDrawer.value = true;
  dagRuns.value = [];
  runsLoading.value = true;
  try {
    const res = await airflowApi.listDagRuns(row.dag_id);
    dagRuns.value = Array.isArray(res) ? res : res?.items || res?.dag_runs || [];
  } catch (e: any) {
    ElMessage.error(`加载运行历史失败: ${e?.message || e}`);
  } finally {
    runsLoading.value = false;
  }
}

async function openRunDetail(run: any) {
  currentRun.value = run;
  runDetailDialog.value = true;
  taskInstances.value = [];
  runDetailLoading.value = true;
  try {
    const res = await airflowApi.getDagRunDetail(currentDag.value.dag_id, run.dag_run_id);
    taskInstances.value = res?.task_instances || res?.taskInstances || [];
    if (res && typeof res === "object" && !res.task_instances) {
      currentRun.value = { ...currentRun.value, ...res };
    }
  } catch (e: any) {
    ElMessage.error(`加载运行详情失败: ${e?.message || e}`);
  } finally {
    runDetailLoading.value = false;
  }
}

async function openLog(task: any) {
  currentTask.value = task;
  logContent.value = "";
  logDialog.value = true;
  await loadLog(task, task.try_number || 1);
}

async function loadLog(task: any, tryNumber: number) {
  if (!task || !currentRun.value) return;
  logLoading.value = true;
  try {
    const res = await airflowApi.getDagRunLog(
      currentDag.value.dag_id,
      currentRun.value.dag_run_id,
      task.task_id,
      tryNumber
    );
    if (typeof res === "string") {
      logContent.value = res;
    } else if (res && typeof res === "object") {
      logContent.value = res.content || res.log || res.data || JSON.stringify(res, null, 2);
    } else {
      logContent.value = "暂无日志";
    }
  } catch (e: any) {
    logContent.value = `加载日志失败: ${e?.message || e}`;
  } finally {
    logLoading.value = false;
  }
}

async function retryTask(task: any) {
  try {
    await ElMessageBox.confirm(
      `确定要重试任务 "${task.task_id}" 吗？`,
      "重试确认",
      { type: "warning" }
    );
    await airflowApi.retryDagRun(currentDag.value.dag_id, currentRun.value.dag_run_id, task.task_id);
    ElMessage.success("重试请求已发送");
    await openRunDetail(currentRun.value);
  } catch (e: any) {
    if (e !== "cancel" && e?.message !== "cancel") {
      ElMessage.error(`重试失败: ${e?.message || e}`);
    }
  }
}

function runStateTag(state?: string): TagType {
  const map: Record<string, TagType> = {
    success: "success",
    running: "warning",
    failed: "danger",
    upstream_failed: "danger",
    queued: "info",
    skipped: "info",
    success_state: "success",
  };
  return map[(state || "").toLowerCase()] || "info";
}

function isFailedState(state?: string): boolean {
  const s = (state || "").toLowerCase();
  return s === "failed" || s === "upstream_failed";
}

function formatDuration(start?: string, end?: string): string {
  if (!start || !end) return "-";
  const startDate = new Date(start).getTime();
  const endDate = new Date(end).getTime();
  if (isNaN(startDate) || isNaN(endDate) || endDate < startDate) return "-";
  const seconds = Math.floor((endDate - startDate) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remSec = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remSec}s`;
  const hours = Math.floor(minutes / 60);
  const remMin = minutes % 60;
  return `${hours}h ${remMin}m`;
}
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  max-height: 60vh;
  overflow: auto;
  font-family: "Consolas", "Monaco", monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
