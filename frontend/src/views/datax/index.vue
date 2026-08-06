<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>DataX 同步任务</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新建同步任务</el-button>
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

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑同步任务' : '新建同步任务'"
      width="700px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="form.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="任务编码" prop="task_code">
          <el-input v-model="form.task_code" placeholder="唯一编码，如 sync_user_to_doris" :disabled="isEdit" />
        </el-form-item>

        <el-divider content-position="left">源端配置</el-divider>
        <el-form-item label="数据源" prop="source_datasource_id">
          <el-select v-model="form.source_datasource_id" placeholder="选择数据源" style="width: 100%;" filterable>
            <el-option
              v-for="ds in datasourceOptions"
              :key="ds.id"
              :label="`${ds.source_name} (${ds.source_type})`"
              :value="ds.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="源表名" prop="source_table">
          <el-input v-model="form.source_table" placeholder="如 user_table" />
        </el-form-item>
        <el-form-item label="Schema">
          <el-input v-model="form.source_schema" placeholder="源端 Schema (可选)" />
        </el-form-item>
        <el-form-item label="WHERE 条件">
          <el-input v-model="form.where_clause" type="textarea" :rows="2" placeholder="增量同步条件，如 updated_at > '2024-01-01'" />
        </el-form-item>
        <el-form-item label="切分主键">
          <el-input v-model="form.split_pk" placeholder="用于 DataX 并行切分的主键 (可选)" />
        </el-form-item>

        <el-divider content-position="left">目标端配置 (Doris)</el-divider>
        <el-form-item label="目标库" prop="target_database">
          <el-input v-model="form.target_database" placeholder="如 ods" />
        </el-form-item>
        <el-form-item label="目标表" prop="target_table">
          <el-input v-model="form.target_table" placeholder="如 ods_user" />
        </el-form-item>

        <el-divider content-position="left">同步选项</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="同步模式">
              <el-select v-model="form.sync_mode" style="width: 100%;">
                <el-option label="全量" value="full" />
                <el-option label="增量" value="incremental" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="并发通道">
              <el-input-number v-model="form.channel" :min="1" :max="10" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 历史抽屉 -->
    <el-drawer
      v-model="historyDrawerVisible"
      :title="`执行历史 - ${currentTaskName}`"
      size="50%"
      direction="rtl"
    >
      <el-table :data="historyData" v-loading="historyLoading" border size="small">
        <el-table-column prop="dag_run_id" label="执行ID" width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="instanceStatusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180" />
        <el-table-column prop="ended_at" label="结束时间" width="180" />
        <el-table-column prop="duration_seconds" label="耗时(秒)" width="100" />
        <el-table-column prop="rows_read" label="读取行数" width="100" />
        <el-table-column prop="rows_written" label="写入行数" width="100" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleViewLog(row)">日志</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 日志对话框 -->
    <el-dialog v-model="logDialogVisible" title="执行日志" width="800px">
      <pre class="log-content">{{ logContent }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataxApi, datasourceApi } from "@/api";

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();
const datasourceOptions = ref<any[]>([]);

const historyDrawerVisible = ref(false);
const historyData = ref<any[]>([]);
const historyLoading = ref(false);
const currentTaskId = ref("");
const currentTaskName = ref("");

const logDialogVisible = ref(false);
const logContent = ref("");

const defaultForm = {
  task_name: "",
  task_code: "",
  source_datasource_id: "",
  source_table: "",
  source_schema: "",
  where_clause: "",
  split_pk: "",
  target_database: "ods",
  target_table: "",
  sync_mode: "full",
  channel: 3,
};

const form = reactive({ ...defaultForm });

const formRules = {
  task_name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
  task_code: [{ required: true, message: "请输入任务编码", trigger: "blur" }],
  source_datasource_id: [{ required: true, message: "请选择数据源", trigger: "change" }],
  source_table: [{ required: true, message: "请输入源表名", trigger: "blur" }],
  target_database: [{ required: true, message: "请输入目标库", trigger: "blur" }],
  target_table: [{ required: true, message: "请输入目标表", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await dataxApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch {
    // handled
  } finally {
    loading.value = false;
  }
}

async function loadDatasourceOptions() {
  try {
    const res = await datasourceApi.list({ page: 1, page_size: 100 });
    datasourceOptions.value = res.items || [];
  } catch {
    // handled
  }
}

function handleAdd() {
  isEdit.value = false;
  Object.assign(form, defaultForm);
  dialogVisible.value = true;
}

function handleEdit(row: any) {
  isEdit.value = true;
  editId.value = row.id;
  Object.assign(form, {
    task_name: row.task_name || "",
    task_code: row.task_code || "",
    source_datasource_id: row.source_datasource_id || "",
    source_table: row.source_table || "",
    source_schema: row.source_schema || "",
    where_clause: row.where_clause || "",
    split_pk: row.split_pk || "",
    target_database: row.target_database || "ods",
    target_table: row.target_table || "",
    sync_mode: row.sync_mode || "full",
    channel: row.channel || 3,
  });
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      if (isEdit.value) {
        await dataxApi.update(editId.value, form);
        ElMessage.success("更新成功");
      } else {
        await dataxApi.create(form);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch {
      // handled
    } finally {
      submitting.value = false;
    }
  });
}

async function handleTrigger(row: any) {
  await ElMessageBox.confirm(`确认立即执行任务 "${row.task_name}"?`, "执行确认");
  try {
    const res = await dataxApi.trigger(row.id);
    ElMessage.success(`任务已触发，执行ID: ${res.dag_run_id}`);
    loadData();
  } catch {
    // handled
  }
}

async function handleHistory(row: any) {
  currentTaskId.value = row.id;
  currentTaskName.value = row.task_name;
  historyDrawerVisible.value = true;
  historyLoading.value = true;
  try {
    const res = await dataxApi.instances(row.id, { page: 1, page_size: 50 });
    historyData.value = res.items || [];
  } catch {
    // handled
  } finally {
    historyLoading.value = false;
  }
}

async function handleViewLog(row: any) {
  try {
    const res = await dataxApi.instanceLog(row.id);
    logContent.value = res.log || res || "暂无日志";
    logDialogVisible.value = true;
  } catch {
    // handled
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除任务 "${row.task_name}"?`, "提示", { type: "warning" });
  await dataxApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function resetForm() {
  formRef.value?.resetFields();
  Object.assign(form, defaultForm);
}

type TagType = "primary" | "success" | "warning" | "info" | "danger";

function statusTag(status: string): TagType {
  const map: Record<string, TagType> = { draft: "info", active: "success", paused: "warning", archived: "info" };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = { draft: "草稿", active: "启用", paused: "暂停", archived: "归档" };
  return map[status] || status;
}

function instanceStatusTag(status: string): TagType {
  const map: Record<string, TagType> = { success: "success", failed: "danger", running: "warning", queued: "info" };
  return map[status] || "info";
}

onMounted(() => {
  loadData();
  loadDatasourceOptions();
});
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.log-content {
  max-height: 500px;
  overflow-y: auto;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: "Courier New", monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
