<template>
  <div class="data-model-page">
    <el-card>
      <template #header>
        <div class="card-header">
        <span>模型设计</span>
          <el-button type="primary" :icon="Plus" @click="handleNewModel">新建模型</el-button>
        </div>
      </template>

      <div class="search-bar">
        <el-input
          v-model="search.keyword"
          placeholder="搜索模型名称/编码"
          clearable
          :prefix-icon="Search"
          style="width: 220px;"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="search.layer" placeholder="分层" clearable style="width: 110px;" @change="handleSearch">
          <el-option label="ODS" value="ods" />
          <el-option label="DWD" value="dwd" />
          <el-option label="DWS" value="dws" />
          <el-option label="ADS" value="ads" />
        </el-select>
        <el-select v-model="search.data_domain" placeholder="数据域" clearable filterable style="width: 130px;" @change="handleSearch">
          <el-option v-for="d in dataDomains" :key="d.domain_code" :label="d.domain_name" :value="d.domain_name" />
        </el-select>
        <el-select v-model="search.business_domain" placeholder="业务过程" clearable filterable style="width: 130px;" @change="handleSearch">
          <el-option v-for="d in businessDomains" :key="d.domain_code" :label="d.domain_name" :value="d.domain_name" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
      </div>

      <el-table :data="modelList" v-loading="loading" border>
        <el-table-column prop="model_name" label="模型名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="分层" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="layerTag(row.layer)" size="small" effect="plain">
              {{ (row.layer || "").toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数据域" width="100">
          <template #default="{ row }">{{ row.data_domain || '-' }}</template>
        </el-table-column>
        <el-table-column label="业务过程" width="100">
          <template #default="{ row }">{{ row.business_domain || '-' }}</template>
        </el-table-column>
        <el-table-column label="库表" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.database }}.{{ row.table_name }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="current_version" label="版本" width="70" align="center" />
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="handlePublish(row)">发布</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新建/编辑基本信息对话框 -->
    <el-dialog v-model="infoDialogVisible" :title="isNewModel ? '新建模型' : '编辑模型'" width="760px" @close="resetInfoForm">
      <el-form ref="infoFormRef" :model="currentModel" :rules="infoRules" label-width="70px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="模型名称" prop="model_name">
              <el-input v-model="currentModel.model_name" placeholder="模型名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分层" prop="layer">
              <el-select v-model="currentModel.layer" style="width: 100%;">
                <el-option label="ODS" value="ods" />
                <el-option label="DWD" value="dwd" />
                <el-option label="DWS" value="dws" />
                <el-option label="ADS" value="ads" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库" prop="database">
              <el-input v-model="currentModel.database" placeholder="如 ods" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据域">
              <el-select
                v-model="currentModel.data_domain"
                placeholder="选择数据域"
                clearable
                filterable
                allow-create
                style="width: 100%;"
              >
                <el-option v-for="d in dataDomains" :key="d.domain_code" :label="d.domain_name" :value="d.domain_name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务过程">
              <el-select
                v-model="currentModel.business_domain"
                placeholder="选择业务过程"
                clearable
                filterable
                allow-create
                style="width: 100%;"
              >
                <el-option v-for="d in businessDomains" :key="d.domain_code" :label="d.domain_name" :value="d.domain_name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="表名" prop="table_name">
              <el-input v-model="currentModel.table_name" placeholder="如 ods_user" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="描述">
              <el-input v-model="currentModel.description" type="textarea" :rows="2" placeholder="模型描述" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="infoDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveInfo">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑模型对话框（基本信息 + 字段设计） -->
    <el-dialog v-model="editDialogVisible" :title="`编辑模型 - ${currentModel.model_name || ''}`" width="920px" top="5vh">
      <el-form ref="editFormRef" :model="currentModel" :rules="infoRules" label-width="70px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="模型名称" prop="model_name">
              <el-input v-model="currentModel.model_name" placeholder="模型名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分层" prop="layer">
              <el-select v-model="currentModel.layer" style="width: 100%;">
                <el-option label="ODS" value="ods" />
                <el-option label="DWD" value="dwd" />
                <el-option label="DWS" value="dws" />
                <el-option label="ADS" value="ads" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库" prop="database">
              <el-input v-model="currentModel.database" placeholder="如 ods" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据域">
              <el-select v-model="currentModel.data_domain" placeholder="选择数据域" clearable filterable allow-create style="width: 100%;">
                <el-option v-for="d in dataDomains" :key="d.domain_code" :label="d.domain_name" :value="d.domain_name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务过程">
              <el-select v-model="currentModel.business_domain" placeholder="选择业务过程" clearable filterable allow-create style="width: 100%;">
                <el-option v-for="d in businessDomains" :key="d.domain_code" :label="d.domain_name" :value="d.domain_name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="表名" prop="table_name">
              <el-input v-model="currentModel.table_name" placeholder="如 ods_user" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="描述">
              <el-input v-model="currentModel.description" type="textarea" :rows="2" placeholder="模型描述" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <el-divider content-position="left">字段设计</el-divider>
      <el-table :data="fields" border size="default" max-height="320">
        <el-table-column type="index" label="#" width="42" />
        <el-table-column label="字段名" width="170">
          <template #default="{ row }">
            <el-input v-model="row.field_name" size="small" placeholder="field_name" @input="regenerateDDL" />
          </template>
        </el-table-column>
        <el-table-column label="字段类型" width="160">
          <template #default="{ row }">
            <el-select v-model="row.field_type" size="small" filterable allow-create style="width: 100%;" @change="regenerateDDL">
              <el-option v-for="t in fieldTypes" :key="t" :label="t" :value="t" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="字段注释" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.field_comment" size="small" placeholder="注释" @input="regenerateDDL" />
          </template>
        </el-table-column>
        <el-table-column label="主键" width="60" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.is_primary_key" @change="regenerateDDL" />
          </template>
        </el-table-column>
        <el-table-column label="分区" width="60" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.is_partition" @change="regenerateDDL" />
          </template>
        </el-table-column>
        <el-table-column label="默认值" width="120">
          <template #default="{ row }">
            <el-input v-model="row.default_value" size="small" placeholder="默认值" @input="regenerateDDL" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ $index }">
            <el-button link type="danger" :icon="Delete" @click="removeField($index)" />
          </template>
        </el-table-column>
      </el-table>

      <div class="field-actions">
        <el-button link type="primary" :icon="Plus" @click="addField">添加字段</el-button>
        <el-button link type="primary" :icon="Clock" @click="openVersionHistory(currentModel)">版本历史</el-button>
      </div>

      <div class="ddl-block">
        <div class="ddl-header">
          <span>DDL 预览</span>
          <el-button link type="primary" :icon="DocumentCopy" @click="copyDDL">复制</el-button>
        </div>
        <pre class="ddl-preview"><code>{{ ddlText }}</code></pre>
      </div>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 版本历史对话框 -->
    <el-dialog v-model="versionDialogVisible" title="版本历史" width="640px">
      <el-empty v-if="!versions.length" description="暂无版本记录" />
      <el-timeline v-else>
        <el-timeline-item
          v-for="v in versions"
          :key="v.id"
          :timestamp="v.created_at"
          placement="top"
          type="primary"
        >
          <el-card shadow="never" class="version-item">
            <div class="version-header">
              <el-tag type="primary" size="small">版本 {{ v.version }}</el-tag>
              <span class="version-time">{{ formatTime(v.created_at) }}</span>
            </div>
            <p class="version-log">{{ v.change_log }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, nextTick } from "vue";
import {
  Plus, Search, RefreshLeft, Delete, DocumentCopy, Clock,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataModelApi } from "@/api";
import { formatDateTime } from "@/utils/format";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const fieldTypes = [
  "BIGINT", "INT", "VARCHAR(255)", "VARCHAR(50)", "DECIMAL(12,2)",
  "DOUBLE", "DATETIME", "DATE", "BOOLEAN", "TEXT",
];

interface ModelField {
  id?: string;
  field_name: string;
  field_type: string;
  field_comment: string;
  is_primary_key: boolean;
  is_partition: boolean;
  default_value: string;
  sort_order: number;
}

interface DataModel {
  id?: string;
  model_name: string;
  model_code: string;
  layer: string;
  database: string;
  table_name: string;
  description: string;
  business_domain?: string;
  data_domain?: string;
  status?: string;
  current_version?: number;
  fields: ModelField[];
}

interface Version {
  id: string;
  version: number;
  change_log: string;
  created_at: string;
}

// ---------- State ----------
const loading = ref(false);
const modelList = ref<DataModel[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const search = reactive({ keyword: "", layer: "", business_domain: "", data_domain: "" });

const selectedModelId = ref("");
const isNewModel = ref(false);
const infoDialogVisible = ref(false);
const editDialogVisible = ref(false);
const saving = ref(false);
const infoFormRef = ref<FormInstance>();
const editFormRef = ref<FormInstance>();

const currentModel = reactive<DataModel>({
  model_name: "",
  model_code: "",
  layer: "ods",
  database: "ods",
  table_name: "",
  description: "",
  business_domain: "",
  data_domain: "",
  status: "draft",
  current_version: 0,
  fields: [],
});

const fields = ref<ModelField[]>([]);
const ddlText = ref("");

const businessDomains = ref<any[]>([]);
const dataDomains = ref<any[]>([]);

const versionDialogVisible = ref(false);
const versions = ref<Version[]>([]);

const infoRules = {
  model_name: [{ required: true, message: "请输入模型名称", trigger: "blur" }],
  layer: [{ required: true, message: "请选择分层", trigger: "change" }],
  database: [{ required: true, message: "请输入数据库", trigger: "blur" }],
  table_name: [{ required: true, message: "请输入表名", trigger: "blur" }],
};

// ---------- DDL Generation ----------
function generateDDL(model: DataModel, modelFields: ModelField[]): string {
  if (!modelFields.length) {
    return `CREATE TABLE IF NOT EXISTS ${model.database || "db"}.${model.table_name || "table"} (\n  -- 暂无字段\n)\nDISTRIBUTED BY HASH(id) BUCKETS 10\nPROPERTIES (\n  'replication_num' = '1'\n);`;
  }
  const sorted = [...modelFields].sort((a, b) => a.sort_order - b.sort_order);
  const cols = sorted.map((f) => {
    let line = `  ${f.field_name || "unnamed"} ${f.field_type || "VARCHAR(255)"}`;
    if (f.is_primary_key) line += " KEY";
    if (f.default_value) line += ` DEFAULT '${f.default_value}'`;
    return line;
  });
  const pk = sorted.filter((f) => f.is_primary_key).map((f) => f.field_name);
  const part = sorted.filter((f) => f.is_partition).map((f) => f.field_name);
  let ddl = `CREATE TABLE IF NOT EXISTS ${model.database || "db"}.${model.table_name || "table"} (\n${cols.join(",\n")}\n)\nDISTRIBUTED BY HASH(${pk.join(", ") || "id"}) BUCKETS 10`;
  if (part.length) ddl += `\nPARTITION BY (${part.join(", ")})`;
  ddl += `\nPROPERTIES (\n  'replication_num' = '1'\n);`;
  return ddl;
}

function regenerateDDL() {
  ddlText.value = generateDDL(currentModel, fields.value);
}

watch(
  () => [currentModel.database, currentModel.table_name],
  () => regenerateDDL()
);
watch(fields, () => regenerateDDL(), { deep: true });

// ---------- Data loading ----------
async function loadData() {
  loading.value = true;
  try {
    const res = await dataModelApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: search.keyword || undefined,
      layer: search.layer || undefined,
      business_domain: search.business_domain || undefined,
      data_domain: search.data_domain || undefined,
    });
    modelList.value = (res.items || []) as DataModel[];
    pagination.total = res.total || 0;
  } catch {
    ElMessage.error("加载模型列表失败");
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.page = 1;
  loadData();
}

function handleReset() {
  Object.assign(search, { keyword: "", layer: "", business_domain: "", data_domain: "" });
  pagination.page = 1;
  loadData();
}

// ---------- Model info ----------
function resetInfoForm() {
  infoFormRef.value?.resetFields();
  Object.assign(currentModel, {
    id: undefined,
    model_name: "",
    model_code: "",
    layer: "ods",
    database: "ods",
    table_name: "",
    description: "",
    business_domain: "",
    data_domain: "",
    status: "draft",
    current_version: 0,
    fields: [],
  });
  fields.value = [];
}

function handleNewModel() {
  isNewModel.value = true;
  selectedModelId.value = "";
  resetInfoForm();
  infoDialogVisible.value = true;
}

function handleEdit(row: DataModel) {
  isNewModel.value = false;
  selectedModelId.value = row.id || "";
  Object.assign(currentModel, {
    ...row,
    fields: (row.fields || []).map((f) => ({ ...f })),
  });
  fields.value = (row.fields || []).map((f) => ({ ...f, sort_order: f.sort_order ?? 0 }));
  regenerateDDL();
  editDialogVisible.value = true;
}

async function handleSaveInfo() {
  if (!infoFormRef.value) return;
  await infoFormRef.value.validate(async (valid) => {
    if (!valid) return;
    saving.value = true;
    try {
      const payload: any = {
        model_name: currentModel.model_name,
        layer: currentModel.layer,
        database: currentModel.database,
        table_name: currentModel.table_name,
        description: currentModel.description || null,
        business_domain: currentModel.business_domain || null,
        data_domain: currentModel.data_domain || null,
      };
      if (isNewModel.value) {
        const created = await dataModelApi.create({ ...payload, fields: [] });
        selectedModelId.value = created.id || created.model_code;
        ElMessage.success("模型创建成功");
      } else {
        await dataModelApi.update(selectedModelId.value, payload);
        ElMessage.success("模型保存成功");
      }
      infoDialogVisible.value = false;
      loadData();
    } catch {
      ElMessage.error("保存失败");
    } finally {
      saving.value = false;
    }
  });
}

function removeField(index: number) {
  fields.value.splice(index, 1);
  fields.value.forEach((f, i) => { f.sort_order = i; });
  regenerateDDL();
}

function addField() {
  fields.value.push({
    field_name: "",
    field_type: "VARCHAR(255)",
    field_comment: "",
    is_primary_key: false,
    is_partition: false,
    default_value: "",
    sort_order: fields.value.length,
  });
  regenerateDDL();
}

async function handleSaveEdit() {
  if (!selectedModelId.value) {
    ElMessage.warning("模型不存在");
    return;
  }
  if (!editFormRef.value) return;
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return;
  saving.value = true;
  try {
    const payload: any = {
      model_name: currentModel.model_name,
      layer: currentModel.layer,
      database: currentModel.database,
      table_name: currentModel.table_name,
      description: currentModel.description || null,
      business_domain: currentModel.business_domain || null,
      data_domain: currentModel.data_domain || null,
      fields: fields.value.map((f, i) => ({
        field_name: f.field_name,
        field_type: f.field_type,
        field_comment: f.field_comment,
        is_primary_key: f.is_primary_key,
        is_partition: f.is_partition,
        default_value: f.default_value,
        sort_order: f.sort_order ?? i,
      })),
    };
    const updated = await dataModelApi.update(selectedModelId.value, payload);
    Object.assign(currentModel, updated);
    ElMessage.success("模型保存成功");
    editDialogVisible.value = false;
    loadData();
  } catch {
    ElMessage.error("保存字段失败");
  } finally {
    saving.value = false;
  }
  });
}

async function openVersionHistory(row: DataModel) {
  const id = row.id || selectedModelId.value;
  if (!id) {
    ElMessage.warning("请先选择模型");
    return;
  }
  try {
    const res = await dataModelApi.versions(id);
    versions.value = (res || []) as Version[];
    versionDialogVisible.value = true;
  } catch {
    ElMessage.error("加载版本历史失败");
  }
}

// ---------- Publish & delete ----------
async function handlePublish(row: DataModel) {
  if (!row.id) return;
  try {
    await ElMessageBox.confirm(
      `确认发布模型 "${row.model_name}"？系统将生成建表语句并在 Doris 中创建 ${row.database}.${row.table_name}。`,
      "发布确认",
      { type: "warning", confirmButtonText: "发布并建表", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await dataModelApi.publish(row.id);
    ElMessage.success("发布成功，建表已完成");
    loadData();
  } catch {
    // handled by interceptor
  }
}

async function handleDelete(row: DataModel) {
  if (!row.id) return;
  await ElMessageBox.confirm(
    `确认删除模型 "${row.model_name}"？将同时删除 Doris 库中的 ${row.database}.${row.table_name} 表。`,
    "删除确认",
    { type: "warning" }
  );
  try {
    await dataModelApi.delete(row.id);
    ElMessage.success("删除成功");
    loadData();
  } catch {
    ElMessage.error("删除失败");
  }
}

// ---------- Copy DDL ----------
async function copyDDL() {
  try {
    await navigator.clipboard.writeText(ddlText.value);
    ElMessage.success("DDL 已复制到剪贴板");
  } catch {
    ElMessage.warning("复制失败，请手动复制");
  }
}

// ---------- Helpers ----------
function layerTag(layer: string): TagType {
  const map: Record<string, TagType> = { ods: "info", dwd: "primary", dws: "warning", ads: "danger" };
  return map[layer] || "info";
}

function formatTime(iso: string | null | undefined): string {
  return formatDateTime(iso);
}

async function loadDomains() {
  try {
    const [b, d] = await Promise.all([
      dataModelApi.businessDomains(),
      dataModelApi.dataDomains(),
    ]);
    businessDomains.value = b || [];
    dataDomains.value = d || [];
  } catch {
    // handled
  }
}

onMounted(() => {
  loadData();
  loadDomains();
});
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.ddl-block {
  .ddl-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .ddl-preview {
    background: #1e1e1e;
    color: #d4d4d4;
    border-radius: 6px;
    padding: 14px;
    margin: 0;
    font-family: "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    line-height: 1.6;
    overflow-x: auto;
    max-height: 260px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;

    code {
      font-family: inherit;
      color: inherit;
    }
  }
}

.version-item {
  .version-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;

    .version-time {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }

  .version-log {
    margin: 0;
    font-size: 14px;
    color: var(--el-text-color-primary);
  }
}
</style>
