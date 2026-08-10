<template>
  <div class="datax-page">
    <!-- ===================== Task List ===================== -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
      <span class="header-title">数据集成</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新建同步任务</el-button>
        </div>
      </template>

      <!-- Filter bar -->
      <div class="filter-bar">
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          clearable
          style="width: 160px"
          @change="handleFilterChange"
        >
          <el-option label="草稿" value="draft" />
          <el-option label="启用" value="active" />
          <el-option label="暂停" value="paused" />
          <el-option label="归档" value="archived" />
        </el-select>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="task_name" label="任务名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="源表" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ sourceTableLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="目标表" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.target_database }}.{{ row.target_table }}</template>
        </el-table-column>
        <el-table-column prop="sync_mode" label="模式" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.sync_mode === 'incremental' ? 'warning' : 'primary'">
              {{ row.sync_mode === 'incremental' ? '增量' : '全量' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="VideoPlay" @click="handleTrigger(row)">执行</el-button>
            <el-button link type="primary" :icon="Clock" @click="handleHistory(row)">历史</el-button>
            <el-button v-if="row.status === 'draft'" link type="primary" @click="handleToggleStatus(row, 'enable')">启用</el-button>
            <el-button v-if="row.status === 'active'" link type="warning" @click="handleToggleStatus(row, 'pause')">暂停</el-button>
            <el-button v-if="row.status === 'paused'" link type="success" @click="handleToggleStatus(row, 'resume')">恢复</el-button>
            <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadData"
        @size-change="handleSizeChange"
        style="margin-top: 16px; justify-content: flex-end"
      />
    </el-card>

    <!-- ===================== Wizard Dialog ===================== -->
    <el-dialog
      v-model="wizardVisible"
      :title="isEdit ? '编辑同步任务' : '新建同步任务'"
      width="880px"
      top="5vh"
      :close-on-click-modal="false"
      @close="handleWizardClose"
    >
      <el-steps :active="currentStep" finish-status="success" align-center class="wizard-steps">
        <el-step title="数据源" />
        <el-step title="目标表" />
        <el-step title="字段映射" />
        <el-step title="同步选项" />
        <el-step title="调度配置" />
        <el-step title="预览保存" />
      </el-steps>

      <div class="wizard-body">
        <!-- Step 1: Select data source -->
        <div v-show="currentStep === 0">
          <el-form ref="step1Ref" :model="form" :rules="step1Rules" label-width="120px">
            <el-form-item label="任务名称" prop="task_name">
              <el-input v-model="form.task_name" placeholder="如：用户表同步到Doris" />
            </el-form-item>
            <el-form-item label="任务编码" prop="task_code">
              <el-input
                v-model="form.task_code"
                placeholder="唯一编码，如 sync_user_to_doris"
                :disabled="isEdit"
              />
            </el-form-item>
            <el-divider content-position="left">源端配置</el-divider>
            <el-form-item label="数据源" prop="source_datasource_id">
              <el-select
                v-model="form.source_datasource_id"
                placeholder="请选择数据源"
                style="width: 100%"
                filterable
                @change="handleDatasourceChange"
              >
                <el-option
                  v-for="ds in datasourceOptions"
                  :key="ds.id"
                  :label="`${ds.source_name} (${ds.source_type})`"
                  :value="ds.id"
                >
                  <span style="float: left">{{ ds.source_name }} ({{ ds.source_type }})</span>
                  <span style="float: right; color: var(--el-text-color-secondary); font-size: 12px">
                    {{ ds.host }}:{{ ds.port }}
                  </span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="源表名" prop="source_table">
              <el-input v-model="form.source_table" placeholder="如 user_table" @blur="handleSourceTableBlur" />
            </el-form-item>
            <el-form-item label="Schema">
              <el-input v-model="form.source_schema" placeholder="源端 Schema（可选）" />
            </el-form-item>
          </el-form>
        </div>

        <!-- Step 2: Configure target table -->
        <div v-show="currentStep === 1">
          <el-form ref="step2Ref" :model="form" :rules="step2Rules" label-width="120px">
            <el-divider content-position="left">目标端配置 (Doris)</el-divider>
            <el-form-item label="目标库" prop="target_database">
              <el-input v-model="form.target_database" placeholder="如 ods" />
            </el-form-item>
            <el-form-item label="目标表" prop="target_table">
              <el-input v-model="form.target_table" placeholder="如 ods_user" />
            </el-form-item>
            <el-form-item label="同步模式" prop="sync_mode">
              <el-radio-group v-model="form.sync_mode">
                <el-radio value="full">全量同步</el-radio>
                <el-radio value="incremental">增量同步</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-alert
              v-if="form.sync_mode === 'incremental'"
              title="增量同步需要在下一步配置 WHERE 条件"
              type="warning"
              :closable="false"
              show-icon
              style="margin-left: 120px; width: fit-content"
            />
          </el-form>
        </div>

        <!-- Step 3: Field mapping -->
        <div v-show="currentStep === 2">
          <div class="step-header">
            <span>字段映射配置</span>
            <el-button type="primary" :icon="Search" size="small" :loading="columnsLoading" @click="loadColumns">
              加载源表字段
            </el-button>
          </div>
          <el-table :data="fieldMappings" border size="small" style="width: 100%; margin-top: 12px" max-height="360">
            <el-table-column type="index" label="#" width="50" align="center" />
            <el-table-column prop="source_column" label="源字段" min-width="140" />
            <el-table-column prop="source_type" label="源类型" width="130">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.source_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="目标字段" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.target_column" placeholder="目标列名" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeMapping($index)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="fieldMappings.length === 0" description="点击「加载源表字段」获取字段列表" />
          <div class="mapping-hint" v-if="fieldMappings.length > 0">
            共 {{ fieldMappings.length }} 个字段映射，目标字段名可编辑
          </div>
        </div>

        <!-- Step 4: Sync options -->
        <div v-show="currentStep === 3">
          <el-form ref="step4Ref" :model="form" :rules="step4Rules" label-width="140px">
            <el-divider content-position="left">同步选项</el-divider>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="并发通道数" prop="channel">
                  <el-input-number v-model="form.channel" :min="1" :max="20" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="错误容忍数" prop="error_limit">
                  <el-input-number v-model="form.error_limit" :min="0" :max="100000" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item
              v-if="form.sync_mode === 'incremental'"
              label="WHERE 条件"
              prop="where_clause"
            >
              <el-input
                v-model="form.where_clause"
                type="textarea"
                :rows="3"
                placeholder="增量同步条件，如 updated_at > '${last_sync_time}'"
              />
              <div class="form-tip">支持变量 ${last_sync_time}，运行时自动替换为上次同步时间</div>
            </el-form-item>
            <el-form-item label="切分主键" prop="split_pk">
              <el-input v-model="form.split_pk" placeholder="用于 DataX 并行切分的主键（可选，如 id）" />
            </el-form-item>
          </el-form>
        </div>

        <!-- Step 5: Schedule -->
        <div v-show="currentStep === 4">
          <el-form ref="step5Ref" :model="form" label-width="140px">
            <el-divider content-position="left">调度配置（可选）</el-divider>
            <el-form-item label="启用调度">
              <el-switch v-model="scheduleEnabled" />
            </el-form-item>
            <el-form-item v-if="scheduleEnabled" label="Cron 表达式" prop="cron_expression">
              <el-input
                v-model="form.cron_expression"
                placeholder="如 0 0 2 * * ?（每天凌晨2点执行）"
              />
            </el-form-item>
            <el-form-item v-if="scheduleEnabled" label="Cron 说明">
              <div class="cron-help">
                <p>秒 分 时 日 月 周（6 或 7 位）</p>
                <p><code>0 0 2 * * ?</code> = 每天凌晨2点</p>
                <p><code>0 */30 * * * ?</code> = 每30分钟</p>
                <p><code>0 0 0 ? * MON</code> = 每周一凌晨</p>
              </div>
            </el-form-item>
            <el-alert
              v-if="!scheduleEnabled"
              title="未启用调度，任务仅支持手动触发执行"
              type="info"
              :closable="false"
              show-icon
            />
          </el-form>
        </div>

        <!-- Step 6: Review -->
        <div v-show="currentStep === 5">
          <el-descriptions title="基本信息" :column="2" border>
            <el-descriptions-item label="任务名称">{{ form.task_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="任务编码">{{ form.task_code || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="源端配置" :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="数据源">{{ datasourceLabel(form.source_datasource_id) }}</el-descriptions-item>
            <el-descriptions-item label="Schema">{{ form.source_schema || '-' }}</el-descriptions-item>
            <el-descriptions-item label="源表">{{ form.source_table || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="目标端配置" :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="目标库">{{ form.target_database || '-' }}</el-descriptions-item>
            <el-descriptions-item label="目标表">{{ form.target_table || '-' }}</el-descriptions-item>
            <el-descriptions-item label="同步模式">
              <el-tag size="small" :type="form.sync_mode === 'incremental' ? 'warning' : 'primary'">
                {{ form.sync_mode === 'incremental' ? '增量' : '全量' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="字段映射" :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="映射数量">{{ fieldMappings.length }} 个字段</el-descriptions-item>
            <el-descriptions-item label="字段列表">
              {{ fieldMappings.map((m) => `${m.source_column}→${m.target_column}`).join(', ') || '-' }}
            </el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="同步选项" :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="并发通道">{{ form.channel }}</el-descriptions-item>
            <el-descriptions-item label="错误容忍">{{ form.error_limit }}</el-descriptions-item>
            <el-descriptions-item label="WHERE 条件" v-if="form.sync_mode === 'incremental'">
              {{ form.where_clause || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="切分主键">{{ form.split_pk || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="调度配置" :column="1" border style="margin-top: 16px">
            <el-descriptions-item label="调度状态">
              {{ scheduleEnabled ? `已启用：${form.cron_expression || '未配置'}` : '未启用' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <template #footer>
        <div class="wizard-footer">
          <el-button @click="wizardVisible = false">取消</el-button>
          <el-button :disabled="currentStep === 0" @click="prevStep">上一步</el-button>
          <el-button
            v-if="currentStep < 5"
            type="primary"
            @click="nextStep"
          >下一步</el-button>
          <el-button
            v-if="currentStep === 5"
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
          >{{ isEdit ? '保存修改' : '创建任务' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ===================== History Drawer ===================== -->
    <el-drawer
      v-model="historyDrawerVisible"
      :title="`执行历史 - ${currentTaskName}`"
      size="55%"
      direction="rtl"
    >
      <div class="drawer-toolbar">
        <el-button :icon="Refresh" size="small" @click="loadHistory">刷新</el-button>
      </div>
      <el-table :data="historyData" v-loading="historyLoading" border size="small" style="width: 100%">
        <el-table-column label="执行ID" width="230" show-overflow-tooltip>
          <template #default="{ row, $index }">{{ formatRunId(row, $index) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="instanceStatusTag(row.status)" size="small">{{ instanceStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="170"><template #default="{ row }">{{ formatDateTime(row.started_at) }}</template></el-table-column>
        <el-table-column label="结束时间" width="170"><template #default="{ row }">{{ formatDateTime(row.ended_at) }}</template></el-table-column>
        <el-table-column prop="duration_seconds" label="耗时(秒)" width="100" align="right" />
        <el-table-column prop="rows_read" label="读取行数" width="100" align="right" />
        <el-table-column prop="rows_written" label="写入行数" width="100" align="right" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleViewLog(row)">日志</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="historyPagination.page"
        :page-size="historyPagination.page_size"
        :total="historyPagination.total"
        layout="total, prev, pager, next"
        @current-change="loadHistory"
        style="margin-top: 12px; justify-content: flex-end"
      />
    </el-drawer>

    <!-- ===================== Log Viewer ===================== -->
    <el-dialog v-model="logDialogVisible" title="执行日志" width="860px" top="5vh">
      <pre class="log-content">{{ logContent }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { formatDateTime } from "@/utils/format";
import {
  Plus,
  Edit,
  Delete,
  VideoPlay,
  Clock,
  Search,
  Refresh,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataxApi, datasourceApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

// ===================== Types =====================
interface FieldMapping {
  source_column: string;
  source_type: string;
  target_column: string;
}

interface DatasourceOption {
  id: string;
  source_name: string;
  source_type: string;
  host: string;
  port: number;
  database_name: string;
}

interface TaskForm {
  task_name: string;
  task_code: string;
  source_datasource_id: string;
  source_table: string;
  source_schema: string;
  target_database: string;
  target_table: string;
  sync_mode: "full" | "incremental";
  channel: number;
  error_limit: number;
  where_clause: string;
  split_pk: string;
  cron_expression: string;
}

// ===================== List State =====================
const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const filterStatus = ref("");

// ===================== Wizard State =====================
const wizardVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const currentStep = ref(0);
const scheduleEnabled = ref(false);

const step1Ref = ref<FormInstance>();
const step2Ref = ref<FormInstance>();
const step4Ref = ref<FormInstance>();
const step5Ref = ref<FormInstance>();

const datasourceOptions = ref<DatasourceOption[]>([]);
const fieldMappings = ref<FieldMapping[]>([]);
const columnsLoading = ref(false);

const defaultForm: TaskForm = {
  task_name: "",
  task_code: "",
  source_datasource_id: "",
  source_table: "",
  source_schema: "",
  target_database: "ods",
  target_table: "",
  sync_mode: "full",
  channel: 3,
  error_limit: 0,
  where_clause: "",
  split_pk: "",
  cron_expression: "",
};

const form = reactive<TaskForm>({ ...defaultForm });

const step1Rules = {
  task_name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
  source_datasource_id: [{ required: true, message: "请选择数据源", trigger: "change" }],
  source_table: [{ required: true, message: "请输入源表名", trigger: "blur" }],
};

const step2Rules = {
  target_database: [{ required: true, message: "请输入目标库", trigger: "blur" }],
  target_table: [{ required: true, message: "请输入目标表", trigger: "blur" }],
  sync_mode: [{ required: true, message: "请选择同步模式", trigger: "change" }],
};

const step4Rules = {
  channel: [{ required: true, message: "请输入并发通道数", trigger: "blur" }],
  where_clause: [{ required: true, message: "增量同步请填写 WHERE 条件", trigger: "blur" }],
};

// ===================== History State =====================
const historyDrawerVisible = ref(false);
const historyData = ref<any[]>([]);
const historyLoading = ref(false);
const historyPagination = reactive({ page: 1, page_size: 50, total: 0 });
const currentTaskId = ref("");

// ===================== Log State =====================
const logDialogVisible = ref(false);
const logContent = ref("");

const currentTaskName = ref("");

// ===================== Data Loading =====================
async function loadData() {
  loading.value = true;
  try {
    const res = await dataxApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      status: filterStatus.value || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false;
  }
}

async function loadDatasourceOptions() {
  try {
    const res = await datasourceApi.list({ page: 1, page_size: 100 });
    datasourceOptions.value = (res.items || []) as DatasourceOption[];
  } catch {
    // handled
  }
}

function datasourceLabel(id: string): string {
  const ds = datasourceOptions.value.find((d) => d.id === id);
  return ds ? `${ds.source_name} (${ds.source_type})` : id || "-";
}

function sourceTableLabel(row: any): string {
  const ds = datasourceOptions.value.find((d) => d.id === row.source_datasource_id);
  const db = ds?.database_name || "";
  return db ? `${db}.${row.source_table}` : row.source_table;
}

function formatRunId(row: any, index: number): string {
  // 任务名 + 8位数字日期 + 两位数字编号，如：测试同步_20260807_01
  const dateStr = formatDateTime(row.created_at || row.started_at).slice(0, 10).replace(/-/g, "");
  const num = String(index + 1).padStart(2, "0");
  return `${currentTaskName.value}_${dateStr}_${num}`;
}

// ===================== Column Loading =====================
async function loadColumns() {
  if (!form.source_datasource_id || !form.source_table) {
    ElMessage.warning("请先选择数据源并填写源表名");
    return;
  }
  columnsLoading.value = true;
  try {
    const cols = await datasourceApi.getColumns(form.source_datasource_id, form.source_table);
    const list = cols || [];
    fieldMappings.value = list.map((c: any) => ({
      source_column: c.column_name,
      source_type: c.column_type,
      target_column: c.column_name, // default same name
    }));
    if (list.length === 0) {
      ElMessage.info("未获取到字段，请检查表名是否正确");
    } else {
      ElMessage.success(`已加载 ${list.length} 个字段`);
    }
  } catch {
    // handled
  } finally {
    columnsLoading.value = false;
  }
}

function handleSourceTableBlur() {
  // Auto-load columns if not yet loaded and user has moved past step 1 conceptually
  if (fieldMappings.value.length === 0 && form.source_datasource_id && form.source_table) {
    // Don't auto-trigger to avoid surprise; user clicks the button in step 3
  }
}

function removeMapping(index: number) {
  fieldMappings.value.splice(index, 1);
}

function handleDatasourceChange() {
  // Clear stale columns when datasource changes
  fieldMappings.value = [];
}

// ===================== Wizard Navigation =====================
async function validateStep(step: number): Promise<boolean> {
  const formRef = [step1Ref, step2Ref, undefined, step4Ref, step5Ref, undefined][step];
  if (!formRef?.value) return true;
  try {
    await formRef.value.validate();
    return true;
  } catch {
    return false;
  }
}

async function nextStep() {
  const valid = await validateStep(currentStep.value);
  if (!valid) {
    ElMessage.warning("请完成当前步骤的必填项");
    return;
  }
  // Extra: step 3 requires at least one mapping
  if (currentStep.value === 2 && fieldMappings.value.length === 0) {
    ElMessage.warning("请加载并配置至少一个字段映射");
    return;
  }
  // Extra: incremental mode on step 4 already has rule
  if (currentStep.value < 5) {
    currentStep.value++;
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}

// ===================== CRUD =====================
function handleAdd() {
  isEdit.value = false;
  Object.assign(form, defaultForm);
  fieldMappings.value = [];
  scheduleEnabled.value = false;
  currentStep.value = 0;
  editId.value = "";
  wizardVisible.value = true;
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
    target_database: row.target_database || "ods",
    target_table: row.target_table || "",
    sync_mode: row.sync_mode || "full",
    channel: row.channel ?? 3,
    error_limit: row.error_limit ?? 0,
    where_clause: row.where_clause || "",
    split_pk: row.split_pk || "",
    cron_expression: row.cron_expression || "",
  });
  // Restore field mappings if present
  fieldMappings.value = Array.isArray(row.field_mappings) && row.field_mappings.length > 0
    ? row.field_mappings.map((m: any) => ({
        source_column: m.source_column || m.sourceColumn || "",
        source_type: m.source_type || m.sourceType || "",
        target_column: m.target_column || m.targetColumn || m.source_column || "",
      }))
    : [];
  scheduleEnabled.value = !!row.cron_expression;
  currentStep.value = 0;
  wizardVisible.value = true;
}

async function handleSubmit() {
  // Final validation
  if (fieldMappings.value.length === 0) {
    ElMessage.warning("请配置字段映射");
    currentStep.value = 2;
    return;
  }
  if (form.sync_mode === "incremental" && !form.where_clause) {
    ElMessage.warning("增量同步请填写 WHERE 条件");
    currentStep.value = 3;
    return;
  }
  if (scheduleEnabled.value && !form.cron_expression) {
    ElMessage.warning("启用调度后请填写 Cron 表达式");
    currentStep.value = 4;
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      ...form,
      field_mappings: fieldMappings.value.map((m) => ({
        source_column: m.source_column,
        source_type: m.source_type,
        target_column: m.target_column,
      })),
      cron_expression: scheduleEnabled.value ? form.cron_expression : "",
    };
    if (isEdit.value) {
      await dataxApi.update(editId.value, payload);
      ElMessage.success("更新成功");
    } else {
      await dataxApi.create(payload);
      ElMessage.success("创建成功");
    }
    wizardVisible.value = false;
    loadData();
  } catch {
    // handled
  } finally {
    submitting.value = false;
  }
}

function handleWizardClose() {
  currentStep.value = 0;
  fieldMappings.value = [];
  scheduleEnabled.value = false;
}

async function handleTrigger(row: any) {
  await ElMessageBox.confirm(`确认立即执行任务 "${row.task_name}"?`, "执行确认", {
    type: "warning",
  });
  try {
    const res = await dataxApi.trigger(row.id);
    ElMessage.success(`任务已触发，执行ID: ${res.dag_run_id}`);
    loadData();
  } catch {
    // handled
  }
}

async function handleToggleStatus(row: any, action: string) {
  try {
    if (action === "pause") {
      await dataxApi.pause(row.id);
      ElMessage.success(`任务 "${row.task_name}" 已暂停`);
    } else if (action === "resume") {
      await dataxApi.resume(row.id);
      ElMessage.success(`任务 "${row.task_name}" 已恢复`);
    } else {
      await dataxApi.update(row.id, { status: "active" });
      ElMessage.success(`任务 "${row.task_name}" 已启用`);
    }
    loadData();
  } catch {
    // handled
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除任务 "${row.task_name}"? 此操作不可恢复。`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    confirmButtonClass: "el-button--danger",
  });
  try {
    await dataxApi.delete(row.id);
    ElMessage.success("删除成功");
    loadData();
  } catch {
    // handled
  }
}

// ===================== History & Log =====================
async function handleHistory(row: any) {
  currentTaskId.value = row.id;
  currentTaskName.value = row.task_name;
  historyDrawerVisible.value = true;
  historyPagination.page = 1;
  await loadHistory();
}

async function loadHistory() {
  historyLoading.value = true;
  try {
    const res = await dataxApi.instances(currentTaskId.value, {
      page: historyPagination.page,
      page_size: historyPagination.page_size,
    });
    historyData.value = res.items || [];
    historyPagination.total = res.total || 0;
  } catch {
    // handled
  } finally {
    historyLoading.value = false;
  }
}

async function handleViewLog(row: any) {
  try {
    const res = await dataxApi.instanceLog(row.id);
    logContent.value = (res as any).log_content || (res as any).log || "暂无日志内容";
    logDialogVisible.value = true;
  } catch {
    // handled
  }
}

// ===================== Filters & Pagination =====================
function handleFilterChange() {
  pagination.page = 1;
  loadData();
}

function handleSizeChange() {
  pagination.page = 1;
  loadData();
}

// ===================== Status Helpers =====================
function statusTag(status: string): TagType {
  const map: Record<string, TagType> = {
    draft: "info",
    active: "success",
    paused: "warning",
    archived: "info",
  };
  return map[status] || "info";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: "草稿",
    active: "启用",
    paused: "暂停",
    archived: "归档",
  };
  return map[status] || status;
}

function instanceStatusTag(status: string): TagType {
  const map: Record<string, TagType> = {
    success: "success",
    failed: "danger",
    running: "warning",
    queued: "info",
    pending: "info",
    killed: "danger",
  };
  return map[status?.toLowerCase()] || "info";
}

function instanceStatusLabel(status: string): string {
  const map: Record<string, string> = {
    success: "成功",
    failed: "失败",
    running: "运行中",
    queued: "排队中",
    pending: "等待",
    killed: "已终止",
  };
  return map[status?.toLowerCase()] || status;
}

// ===================== Init =====================
onMounted(() => {
  loadData();
  loadDatasourceOptions();
});
</script>

<style lang="scss" scoped>
.datax-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-title {
      font-size: 16px;
      font-weight: 600;
    }
  }

  .filter-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    align-items: center;
  }

  // Wizard
  .wizard-steps {
    margin-bottom: 24px;
  }

  .wizard-body {
    min-height: 300px;
    max-height: 55vh;
    overflow-y: auto;
    padding: 0 4px;
  }

  .step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    font-size: 14px;
  }

  .mapping-hint {
    margin-top: 8px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
    line-height: 1.4;
  }

  .wizard-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  // Cron help
  .cron-help {
    p {
      margin: 4px 0;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
    code {
      background: var(--el-fill-color-light);
      padding: 2px 6px;
      border-radius: 3px;
      font-family: "Courier New", monospace;
    }
  }

  // Drawer
  .drawer-toolbar {
    margin-bottom: 12px;
  }

  // Log viewer
  .log-content {
    max-height: 60vh;
    overflow-y: auto;
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 4px;
    font-family: "Courier New", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
  }
}
</style>
