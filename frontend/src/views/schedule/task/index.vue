<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>调度任务</span>
        <div class="actions">
          <el-button type="primary" :icon="Plus" @click="openCreate">新建调度脚本</el-button>
          <el-button type="primary" :icon="RefreshLeft" :loading="dagLoading" @click="loadDags">同步 DAG 列表</el-button>
        </div>
      </div>
    </template>

    <el-table :data="dagTable" v-loading="dagLoading" border>
      <el-table-column prop="dag_id" label="DAG 名称" min-width="220" show-overflow-tooltip />
      <el-table-column prop="fileloc" label="文件位置" min-width="280" show-overflow-tooltip />
      <el-table-column label="调度" width="150">
        <template #default="{ row }">
          <el-tag v-if="dagSchedule(row)" type="warning" effect="plain">{{ dagSchedule(row) }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_paused ? 'info' : 'success'" size="small">
            {{ row.is_paused ? '已暂停' : '运行中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDagDetail(row)">运行记录</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link :type="row.is_paused ? 'success' : 'warning'" @click="handleTogglePause(row)">
            {{ row.is_paused ? '恢复' : '暂停' }}
          </el-button>
          <el-button link type="success" @click="handleTriggerDag(row)">触发</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 新建 / 编辑调度脚本（.py DAG 文件） -->
  <el-dialog v-model="scriptDialogVisible" :title="editMode ? `编辑脚本 - ${currentDagId}` : '新建调度脚本'" width="820px" @close="resetScriptDialog">
    <el-form label-width="90px">
      <el-form-item v-if="!editMode" label="脚本名称" required>
        <el-input v-model="scriptName" placeholder="用于生成 .py 文件名，如：每日费用汇总" maxlength="60" />
      </el-form-item>
      <el-form-item v-if="editMode" label="DAG 名称">
        <el-input :model-value="currentDagId" disabled />
      </el-form-item>
      <el-form-item v-if="editMode" label="文件位置">
        <el-input :model-value="currentFileloc" disabled />
      </el-form-item>
      <el-form-item v-if="!editMode" label="脚本模板">
        <el-radio-group v-model="scriptRuntime" @change="handleTemplateChange">
          <el-radio-button value="python">Python</el-radio-button>
          <el-radio-button value="pyspark">PySpark</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="脚本内容">
        <div ref="editorRef" class="script-editor"></div>
      </el-form-item>
    </el-form>
    <div class="dialog-hint">
      脚本为 Airflow DAG 定义（Python/PySpark），请包含 dag_id 和 schedule；保存前校验 Python 语法，保存后由 Airflow 自动解析。PySpark 默认使用 LocalExecutor 容器内的 local[2] 模式。
    </div>
    <template #footer>
      <el-button @click="scriptDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSaveScript">保存</el-button>
    </template>
  </el-dialog>

  <!-- DAG 运行记录 -->
  <el-dialog v-model="dagDialogVisible" :title="`运行记录 - ${currentDag?.dag_id || ''}`" width="900px">
    <el-table :data="dagRuns" v-loading="dagRunsLoading" border>
      <el-table-column prop="dag_run_id" label="Run ID" min-width="200" show-overflow-tooltip />
      <el-table-column label="运行类型" width="110">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ runTypeLabel(row.run_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="stateType(row.state)" size="small">{{ row.state || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.start_date) }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.end_date) }}</template>
      </el-table-column>
    </el-table>
    <template #footer>
      <el-button @click="dagDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { Plus, RefreshLeft } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { airflowApi } from "@/api";
import { formatDateTime } from "@/utils/format";
import CodeMirror from "codemirror";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/python/python";
import "codemirror/addon/edit/matchbrackets";
import "codemirror/addon/edit/closebrackets";
import "codemirror/theme/material-darker.css";

// ---------- Airflow DAG 列表 ----------
const dagLoading = ref(false);
const dagTable = ref<any[]>([]);

async function loadDags() {
  dagLoading.value = true;
  try {
    const res = await airflowApi.listDags(100, 0);
    dagTable.value = res || [];
  } catch {
    // handled
  } finally {
    dagLoading.value = false;
  }
}

function dagSchedule(row: any): string {
  const si = row.timetable_summary || row.schedule_interval;
  if (!si) return "";
  return typeof si === "string" ? si : si.value || "";
}

// ---------- 新建 / 编辑脚本 ----------
const scriptDialogVisible = ref(false);
const editMode = ref(false);
const saving = ref(false);
const scriptName = ref("");
const scriptRuntime = ref<"python" | "pyspark">("python");
const currentDagId = ref("");
const currentFileloc = ref("");
const editorRef = ref<HTMLElement | null>(null);
let cmInstance: any = null;

const DAG_TEMPLATE = `import json
import logging
import os
import urllib.request
from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator

default_args = {"owner": "datamind", "retries": 0}

dag = DAG(
    dag_id="example_dag",
    description="示例调度脚本",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["datamind"],
    default_args=default_args,
)


SQL = """-- 将这里替换为任务实际执行的 INSERT/CREATE TABLE AS SELECT SQL"""


def report_lineage(context, state):
    api_url = os.environ.get("DATAMIND_API_URL", "")
    token = os.environ.get("LINEAGE_EVENT_TOKEN") or os.environ.get("EXECUTOR_TOKEN", "")
    if not api_url or not token:
        return
    payload = {
        "dag_id": context["dag"].dag_id,
        "dag_run_id": context["dag_run"].run_id,
        "task_id": context["task_instance"].task_id,
        "try_number": context["task_instance"].try_number,
        "state": state,
        "operator_type": context["task"].__class__.__name__,
        "sql": SQL,
        "datasource_name": "Doris 数仓",
        "default_database": "dwd",
        "start_date": context["task_instance"].start_date.isoformat() if context["task_instance"].start_date else None,
    }
    request = urllib.request.Request(
        api_url.rstrip("/") + "/api/v1/internal/lineage/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Lineage-Token": token},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=15).read()
    except Exception:
        logging.exception("DataMind lineage callback failed; active run sync will retry collection")


def lineage_success(context):
    report_lineage(context, "success")


def lineage_failure(context):
    report_lineage(context, "failed")


def run_task():
    print("task running")


t1 = PythonOperator(
    task_id="run_task",
    python_callable=run_task,
    on_success_callback=lineage_success,
    on_failure_callback=lineage_failure,
    dag=dag,
)
`;

const PYSPARK_DAG_TEMPLATE = `import os
from datetime import datetime, timezone

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator

default_args = {"owner": "datamind", "retries": 0}

dag = DAG(
    dag_id="example_pyspark_dag",
    description="PySpark 本地模式示例任务",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["datamind", "pyspark"],
    default_args=default_args,
)


def run_pyspark_job():
    from pyspark.sql import SparkSession, functions as F

    spark = (
        SparkSession.builder
        .master(os.environ.get("SPARK_MASTER", "local[2]"))
        .appName("datamind-example-pyspark")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
        .getOrCreate()
    )
    try:
        result = (
            spark.range(0, 100)
            .withColumn("bucket", F.col("id") % 10)
            .groupBy("bucket")
            .count()
            .orderBy("bucket")
        )
        result.show(20, truncate=False)
    finally:
        spark.stop()


run_job = PythonOperator(
    task_id="run_pyspark_job",
    python_callable=run_pyspark_job,
    dag=dag,
)
`;

function ensureEditor() {
  if (!cmInstance && editorRef.value) {
    cmInstance = CodeMirror(editorRef.value, {
      value: "",
      mode: "text/x-python",
      theme: "material-darker",
      lineNumbers: true,
      matchBrackets: true,
      autoCloseBrackets: true,
    });
  }
}

function setEditorContent(content: string) {
  if (cmInstance) {
    cmInstance.setValue(content);
  } else {
    // 首次打开时由 CodeMirror 初始化后写入
    nextTick(() => cmInstance?.setValue(content));
  }
}

function openCreate() {
  editMode.value = false;
  scriptRuntime.value = "python";
  scriptName.value = "";
  currentDagId.value = "";
  currentFileloc.value = "";
  scriptDialogVisible.value = true;
  nextTick(() => {
    ensureEditor();
    setEditorContent(DAG_TEMPLATE);
  });
}

function handleTemplateChange(value: string | number | boolean | undefined) {
  setEditorContent(value === "pyspark" ? PYSPARK_DAG_TEMPLATE : DAG_TEMPLATE);
}

async function openEdit(row: any) {
  editMode.value = true;
  currentDagId.value = row.dag_id;
  currentFileloc.value = row.fileloc || "";
  scriptDialogVisible.value = true;
  await nextTick();
  ensureEditor();
  setEditorContent("// 加载中...");
  try {
    const res = await airflowApi.getDagFile(row.dag_id);
    currentFileloc.value = res.fileloc || row.fileloc || "";
    setEditorContent(res.content || "");
  } catch {
    setEditorContent("");
  }
}

function resetScriptDialog() {
  scriptName.value = "";
  currentDagId.value = "";
  currentFileloc.value = "";
}

async function handleSaveScript() {
  const content = cmInstance ? cmInstance.getValue() : "";
  if (!content.trim()) {
    ElMessage.warning("脚本内容不能为空");
    return;
  }
  saving.value = true;
  try {
    if (editMode.value) {
      const res: any = await airflowApi.updateDagFile(currentDagId.value, content);
      ElMessage.success(`已保存${res?.uses_pyspark ? "（PySpark）" : ""}，Airflow 将自动重新解析`);
    } else {
      if (!scriptName.value.trim()) {
        ElMessage.warning("请输入脚本名称");
        return;
      }
      const res = await airflowApi.createDagFile({
        script_name: scriptName.value.trim(),
        content,
      });
      ElMessage.success(`已部署${res?.uses_pyspark ? " PySpark" : ""}：${res.fileloc}，Airflow 1~5 分钟内自动解析`);
    }
    scriptDialogVisible.value = false;
    loadDags();
  } catch (e: any) {
    ElMessage.error(e?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

// ---------- 运行记录 / 启停 / 触发 ----------
const dagDialogVisible = ref(false);
const dagRunsLoading = ref(false);
const dagRuns = ref<any[]>([]);
const currentDag = ref<any>(null);

type TagType = "primary" | "success" | "warning" | "info" | "danger";

function stateType(state: string): TagType {
  const map: Record<string, TagType> = {
    success: "success",
    failed: "danger",
    running: "warning",
    queued: "info",
  };
  return map[state] || "info";
}

function runTypeLabel(t: string): string {
  const map: Record<string, string> = {
    manual: "手动触发",
    scheduled: "定时调度",
    backfill: "补数据",
    dataset_triggered: "数据触发",
  };
  return map[t] || t || "-";
}

async function openDagDetail(row: any) {
  currentDag.value = row;
  dagDialogVisible.value = true;
  dagRuns.value = [];
  await loadDagRuns(row.dag_id);
}

async function loadDagRuns(dagId: string) {
  dagRunsLoading.value = true;
  try {
    const res = await airflowApi.listDagRuns(dagId, 20, 0);
    dagRuns.value = res || [];
  } catch {
    dagRuns.value = [];
  } finally {
    dagRunsLoading.value = false;
  }
}

async function handleTogglePause(row: any) {
  try {
    if (row.is_paused) {
      await ElMessageBox.confirm(`确认恢复 DAG "${row.dag_id}" 的调度？`, "恢复确认", { type: "warning" });
      await airflowApi.resumeDag(row.dag_id);
      ElMessage.success("已恢复调度");
    } else {
      await ElMessageBox.confirm(`确认暂停 DAG "${row.dag_id}"？暂停后将不再按计划触发。`, "暂停确认", { type: "warning" });
      await airflowApi.pauseDag(row.dag_id);
      ElMessage.success("已暂停");
    }
    loadDags();
  } catch (e: any) {
    if (e !== "cancel" && e?.message !== "cancel") {
      ElMessage.error(e?.message || "操作失败");
    }
  }
}

async function handleTriggerDag(row: any) {
  try {
    await ElMessageBox.confirm(`确认立即触发 DAG "${row.dag_id}" 执行一次？`, "触发确认", { type: "warning" });
    const res = await airflowApi.triggerDag(row.dag_id, {});
    ElMessage.success(`已触发：${res?.dag_run_id || ""}`);
    loadDags();
  } catch (e: any) {
    if (e !== "cancel" && e?.message !== "cancel") {
      ElMessage.error(e?.message || "触发失败");
    }
  }
}

onMounted(() => {
  loadDags();
});

onBeforeUnmount(() => {
  if (cmInstance) {
    try {
      const wrapper = (cmInstance as any).getWrapperElement?.();
      if (wrapper && wrapper.parentNode) {
        wrapper.parentNode.removeChild(wrapper);
      }
    } catch {
      // ignore
    }
    cmInstance = null;
  }
});
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 8px;
}

.dialog-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: -4px;
  margin-bottom: 12px;
}

.script-editor {
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;

  :deep(.CodeMirror) {
    font-family: "Courier New", monospace;
    font-size: 13px;
    height: 360px;
  }
}
</style>
