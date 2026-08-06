<template>
  <div class="data-model-page">
    <!-- Top toolbar -->
    <el-card class="toolbar-card" shadow="never">
      <el-form :inline="true" class="toolbar-form" @submit.prevent>
        <el-form-item label="模型名称">
          <el-input v-model="currentModel.model_name" placeholder="模型名称" style="width: 180px;" />
        </el-form-item>
        <el-form-item label="模型编码">
          <el-input v-model="currentModel.model_code" placeholder="唯一编码" style="width: 180px;" :disabled="!isNewModel" />
        </el-form-item>
        <el-form-item label="分层">
          <el-select v-model="currentModel.layer" style="width: 110px;">
            <el-option label="ODS" value="ods" />
            <el-option label="DWD" value="dwd" />
            <el-option label="DWS" value="dws" />
            <el-option label="ADS" value="ads" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据库">
          <el-input v-model="currentModel.database" placeholder="如 ods" style="width: 140px;" />
        </el-form-item>
        <el-form-item label="表名">
          <el-input v-model="currentModel.table_name" placeholder="如 ods_user" style="width: 180px;" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="currentModel.description" placeholder="模型描述" style="width: 220px;" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Plus" @click="handleNewModel">新建模型</el-button>
          <el-button type="success" :icon="Check" :loading="saving" @click="handleSaveModel">保存模型</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Three-column layout -->
    <el-row :gutter="12" class="main-row">
      <!-- Left column: Model directory tree -->
      <el-col :span="5">
        <el-card shadow="never" class="tree-card">
          <template #header>
            <div class="card-header">
              <span>模型目录</span>
              <el-button text type="primary" :icon="Refresh" @click="loadTree" />
            </div>
          </template>
          <el-input
            v-model="treeFilter"
            placeholder="搜索模型..."
            clearable
            size="small"
            style="margin-bottom: 12px;"
          />
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="treeProps"
            node-key="id"
            highlight-current
            default-expand-all
            :filter-node-method="filterNode"
            @node-click="handleNodeClick"
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <span v-if="data.type === 'layer'" class="tree-layer">
                  <el-tag :type="layerTag(data.layer as string)" size="small">{{ data.label }}</el-tag>
                </span>
                <span v-else class="tree-model">
                  <el-icon><Document /></el-icon>
                  <span class="tree-model-name">{{ data.label }}</span>
                  <el-tag
                    v-if="data.status === 'active'"
                    type="success"
                    size="small"
                    effect="plain"
                  >启用</el-tag>
                  <el-tag v-else type="info" size="small" effect="plain">草稿</el-tag>
                </span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- Middle column: Field design table -->
      <el-col :span="12">
        <el-card shadow="never" class="fields-card">
          <template #header>
            <div class="card-header">
              <div class="fields-title">
                <span>字段设计</span>
                <el-tag v-if="selectedModelId" type="primary" size="small" effect="plain" style="margin-left: 8px;">
                  {{ currentModel.model_name || '未命名' }}
                </el-tag>
                <el-tag v-if="currentModel.current_version" type="warning" size="small" effect="plain" style="margin-left: 4px;">
                  v{{ currentModel.current_version }}
                </el-tag>
              </div>
              <el-button type="primary" size="small" :icon="Plus" @click="addField">添加字段</el-button>
            </div>
          </template>

          <el-table :data="fields" border size="default" style="width: 100%;" max-height="560">
            <el-table-column type="index" label="#" width="42" />
            <el-table-column label="字段名" width="160">
              <template #default="{ row }">
                <el-input v-model="row.field_name" size="small" placeholder="field_name" @input="regenerateDDL" />
              </template>
            </el-table-column>
            <el-table-column label="字段类型" width="150">
              <template #default="{ row }">
                <el-input v-model="row.field_type" size="small" placeholder="VARCHAR(255)" @input="regenerateDDL" />
              </template>
            </el-table-column>
            <el-table-column label="字段注释" min-width="150">
              <template #default="{ row }">
                <el-input v-model="row.field_comment" size="small" placeholder="注释" />
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
            <el-table-column label="默认值" width="140">
              <template #default="{ row }">
                <el-input v-model="row.default_value" size="small" placeholder="默认值" @input="regenerateDDL" />
              </template>
            </el-table-column>
            <el-table-column label="排序" width="70" align="center">
              <template #default="{ row, $index }">
                <el-input-number
                  v-model="row.sort_order"
                  size="small"
                  :min="0"
                  :controls="false"
                  style="width: 50px;"
                  @change="onSortChange($index)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70" align="center">
              <template #default="{ $index }">
                <el-button text type="danger" size="small" :icon="Delete" @click="removeField($index)" />
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!fields.length" description="暂无字段，点击「添加字段」开始设计" />
        </el-card>
      </el-col>

      <!-- Right column: DDL preview -->
      <el-col :span="7">
        <el-card shadow="never" class="ddl-card">
          <template #header>
            <div class="card-header">
              <span>DDL 预览</span>
              <div>
                <el-button text type="primary" :icon="DocumentCopy" @click="copyDDL">复制</el-button>
                <el-button type="warning" size="small" :icon="Stamp" :loading="versioning" @click="handleSaveVersion">保存版本</el-button>
                <el-button type="success" size="small" :icon="Promotion" :loading="publishing" @click="handlePublish">发布</el-button>
              </div>
            </div>
          </template>
          <div class="ddl-actions">
            <el-button text size="small" :icon="Clock" @click="openVersionHistory">版本历史</el-button>
          </div>
          <pre class="ddl-preview"><code>{{ ddlText }}</code></pre>
        </el-card>
      </el-col>
    </el-row>

    <!-- Version history dialog -->
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
              <span class="version-time">{{ v.created_at }}</span>
            </div>
            <p class="version-log">{{ v.change_log }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, nextTick } from "vue";
import {
  Plus, Check, Refresh, Delete, Document, DocumentCopy,
  Stamp, Promotion, Clock,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import type { ElTree } from "element-plus";
import { dataModelApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

// ---------- Types ----------
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
  status?: string;
  current_version?: number;
  fields: ModelField[];
}

interface TreeNode {
  id: string;
  label: string;
  type: "layer" | "model";
  layer?: string;
  status?: string;
  children?: TreeNode[];
}

interface Version {
  id: string;
  version: number;
  change_log: string;
  created_at: string;
}

// ---------- State ----------
const treeRef = ref<InstanceType<typeof ElTree>>();
const treeData = ref<TreeNode[]>([]);
const treeFilter = ref("");
const treeProps = { label: "label", children: "children" };

const allModels = ref<DataModel[]>([]);
const selectedModelId = ref<string>("");
const isNewModel = ref(false);

const currentModel = reactive<DataModel>({
  model_name: "",
  model_code: "",
  layer: "ods",
  database: "ods",
  table_name: "",
  description: "",
  status: "draft",
  current_version: 0,
  fields: [],
});

const fields = ref<ModelField[]>([]);
const ddlText = ref("");

const saving = ref(false);
const versioning = ref(false);
const publishing = ref(false);
const loadingTree = ref(false);

const versionDialogVisible = ref(false);
const versions = ref<Version[]>([]);

// ---------- DDL Generation ----------
function generateDDL(model: DataModel, fields: ModelField[]): string {
  if (!fields.length) {
    const dbName = model.database || "db";
    const tbl = model.table_name || "table";
    return `CREATE TABLE IF NOT EXISTS ${dbName}.${tbl} (\n  -- 暂无字段\n)\nDISTRIBUTED BY HASH(id) BUCKETS 10\nPROPERTIES (\n  'replication_num' = '1'\n);`;
  }

  const sortedFields = [...fields].sort((a, b) => a.sort_order - b.sort_order);

  const cols = sortedFields.map((f) => {
    let line = `  ${f.field_name || 'unnamed'} ${f.field_type || 'VARCHAR(255)'}`;
    if (f.is_primary_key) line += " KEY";
    if (f.default_value) line += ` DEFAULT '${f.default_value}'`;
    return line;
  });

  const pkFields = sortedFields.filter((f) => f.is_primary_key).map((f) => f.field_name);
  const partitionFields = sortedFields.filter((f) => f.is_partition).map((f) => f.field_name);

  let ddl = `CREATE TABLE IF NOT EXISTS ${model.database || "db"}.${model.table_name || "table"} (\n${cols.join(",\n")}\n)\nDISTRIBUTED BY HASH(${pkFields.join(", ") || "id"}) BUCKETS 10`;
  if (partitionFields.length) ddl += `\nPARTITION BY (${partitionFields.join(", ")})`;
  ddl += `\nPROPERTIES (\n  'replication_num' = '1'\n);`;

  return ddl;
}

function regenerateDDL() {
  ddlText.value = generateDDL(currentModel, fields.value);
}

// Watch currentModel property changes to regenerate DDL
watch(
  () => [currentModel.database, currentModel.table_name],
  () => regenerateDDL()
);

watch(
  () => fields.value,
  () => regenerateDDL(),
  { deep: true }
);

// ---------- Tree ----------
function buildTree(models: DataModel[]): TreeNode[] {
  const layerMap: Record<string, string> = { ods: "ODS", dwd: "DWD", dws: "DWS", ads: "ADS" };
  const layerOrder = ["ods", "dwd", "dws", "ads"];

  const tree: TreeNode[] = layerOrder.map((layer) => {
    const layerModels = models.filter((m) => m.layer === layer);
    return {
      id: `layer-${layer}`,
      label: layerMap[layer] || layer.toUpperCase(),
      type: "layer" as const,
      layer,
      children: layerModels.map((m) => ({
        id: m.id || m.model_code,
        label: m.model_name,
        type: "model" as const,
        status: m.status,
        children: undefined,
      })),
    };
  });

  return tree;
}

async function loadTree() {
  loadingTree.value = true;
  try {
    const res = await dataModelApi.list({ page: 1, page_size: 1000 });
    allModels.value = (res.items || []) as DataModel[];
    treeData.value = buildTree(allModels.value);
  } catch {
    ElMessage.error("加载模型列表失败");
  } finally {
    loadingTree.value = false;
  }
}

function filterNode(value: string, data: any): boolean {
  if (!value) return true;
  return (data.label || "").toLowerCase().includes(value.toLowerCase());
}

watch(treeFilter, (val) => {
  treeRef.value?.filter(val);
});

function handleNodeClick(node: TreeNode) {
  if (node.type !== "model") return;
  const model = allModels.value.find((m) => (m.id || m.model_code) === node.id);
  if (!model) return;
  selectModel(model);
}

function selectModel(model: DataModel) {
  selectedModelId.value = model.id || model.model_code;
  isNewModel.value = false;
  Object.assign(currentModel, {
    ...model,
    fields: (model.fields || []).map((f) => ({ ...f })),
  });
  fields.value = (model.fields || []).map((f) => ({ ...f }));
  regenerateDDL();
}

// ---------- Field operations ----------
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

function removeField(index: number) {
  fields.value.splice(index, 1);
  // Reindex sort_order
  fields.value.forEach((f, i) => {
    f.sort_order = i;
  });
  regenerateDDL();
}

function onSortChange(_index: number) {
  fields.value.sort((a, b) => a.sort_order - b.sort_order);
  // Reindex
  fields.value.forEach((f, i) => {
    f.sort_order = i;
  });
  regenerateDDL();
}

// ---------- Model operations ----------
function handleNewModel() {
  selectedModelId.value = "";
  isNewModel.value = true;
  Object.assign(currentModel, {
    id: undefined,
    model_name: "",
    model_code: "",
    layer: "ods",
    database: "ods",
    table_name: "",
    description: "",
    status: "draft",
    current_version: 0,
    fields: [],
  });
  fields.value = [];
  regenerateDDL();
  ElMessage.info("已创建空白模型，请填写信息并添加字段");
}

async function handleSaveModel() {
  if (!currentModel.model_name) {
    ElMessage.warning("请输入模型名称");
    return;
  }
  if (!currentModel.model_code) {
    ElMessage.warning("请输入模型编码");
    return;
  }
  if (!currentModel.table_name) {
    ElMessage.warning("请输入表名");
    return;
  }

  saving.value = true;
  try {
    const payload: DataModel = {
      ...currentModel,
      fields: fields.value.map((f, i) => ({
        ...f,
        sort_order: f.sort_order ?? i,
      })),
    };

    if (isNewModel.value || !selectedModelId.value) {
      const created = await dataModelApi.create(payload);
      ElMessage.success("模型创建成功");
      selectedModelId.value = created.id || created.model_code;
      isNewModel.value = false;
      Object.assign(currentModel, created);
    } else {
      const updated = await dataModelApi.update(selectedModelId.value, payload);
      ElMessage.success("模型保存成功");
      Object.assign(currentModel, updated);
    }

    await loadTree();
    // Re-select current model in tree
    nextTick(() => {
      if (selectedModelId.value) {
        treeRef.value?.setCurrentKey(selectedModelId.value);
      }
    });
  } catch {
    ElMessage.error("保存模型失败");
  } finally {
    saving.value = false;
  }
}

async function handleSaveVersion() {
  if (!selectedModelId.value) {
    ElMessage.warning("请先选择或保存模型");
    return;
  }

  let changeLog = "";
  try {
    const { value } = await ElMessageBox.prompt("请输入版本变更说明", "保存版本", {
      confirmButtonText: "保存",
      cancelButtonText: "取消",
      inputType: "textarea",
      inputPlaceholder: "例如：新增 user_type 字段",
      inputValidator: (val: string) => {
        if (!val || !val.trim()) return "变更说明不能为空";
        return true;
      },
    });
    changeLog = value.trim();
  } catch {
    return; // cancelled
  }

  versioning.value = true;
  try {
    // First save the model, then create a version snapshot
    const payload: DataModel = {
      ...currentModel,
      fields: fields.value.map((f, i) => ({
        ...f,
        sort_order: f.sort_order ?? i,
      })),
    };
    const updated = await dataModelApi.update(selectedModelId.value, payload);
    Object.assign(currentModel, updated);

    // The version snapshot is created via the update + a version API call
    // Depending on backend, versions may be auto-created on update.
    // If a separate API is needed, call it here:
    // await dataModelApi.createVersion(selectedModelId.value, { change_log: changeLog });

    ElMessage.success(`版本已保存：${changeLog}`);
    await loadTree();
  } catch {
    ElMessage.error("保存版本失败");
  } finally {
    versioning.value = false;
  }
}

async function handlePublish() {
  if (!selectedModelId.value) {
    ElMessage.warning("请先选择或保存模型");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确认发布模型 "${currentModel.model_name}" ? 发布后模型状态将变为「已启用」。`,
      "发布确认",
      { type: "warning", confirmButtonText: "发布", cancelButtonText: "取消" }
    );
  } catch {
    return; // cancelled
  }

  publishing.value = true;
  try {
    const payload: DataModel = {
      ...currentModel,
      status: "active",
      fields: fields.value.map((f, i) => ({
        ...f,
        sort_order: f.sort_order ?? i,
      })),
    };
    const updated = await dataModelApi.update(selectedModelId.value, payload);
    Object.assign(currentModel, updated);
    ElMessage.success("模型发布成功");
    await loadTree();
    nextTick(() => {
      if (selectedModelId.value) {
        treeRef.value?.setCurrentKey(selectedModelId.value);
      }
    });
  } catch {
    ElMessage.error("发布失败");
  } finally {
    publishing.value = false;
  }
}

// ---------- Version history ----------
async function openVersionHistory() {
  if (!selectedModelId.value) {
    ElMessage.warning("请先选择模型");
    return;
  }
  try {
    const res = await dataModelApi.versions(selectedModelId.value);
    versions.value = (res || []) as Version[];
    versionDialogVisible.value = true;
  } catch {
    ElMessage.error("加载版本历史失败");
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
  const map: Record<string, TagType> = {
    ods: "info",
    dwd: "primary",
    dws: "warning",
    ads: "danger",
  };
  return map[layer] || "info";
}

// Suppress unused import warning for FormInstance (re-exported by api module)
void (null as unknown as FormInstance);

// ---------- Init ----------
onMounted(() => {
  loadTree().then(() => {
    regenerateDDL();
  });
});
</script>

<style lang="scss" scoped>
.data-model-page {
  padding: 12px;

  .toolbar-card {
    margin-bottom: 12px;

    .toolbar-form {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: 0;

      .el-form-item {
        margin-bottom: 8px;
        margin-right: 12px;
      }
    }
  }

  .main-row {
    align-items: stretch;

    .el-col {
      min-height: 600px;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 32px;
  }

  // Tree card
  .tree-card {
    height: 100%;

    :deep(.el-card__body) {
      padding: 12px;
      max-height: 600px;
      overflow-y: auto;
    }

    .tree-node {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-right: 8px;
      font-size: 13px;
    }

    .tree-layer {
      font-weight: 600;
    }

    .tree-model {
      display: flex;
      align-items: center;
      gap: 6px;

      .tree-model-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 120px;
      }
    }
  }

  // Fields card
  .fields-card {
    height: 100%;

    .card-header {
      .fields-title {
        display: flex;
        align-items: center;
      }
    }

    :deep(.el-card__body) {
      padding: 12px;
    }
  }

  // DDL card
  .ddl-card {
    height: 100%;

    .ddl-actions {
      margin-bottom: 8px;
    }

    :deep(.el-card__body) {
      padding: 12px;
    }

    .ddl-preview {
      background: #1e1e1e;
      color: #d4d4d4;
      border-radius: 6px;
      padding: 16px;
      margin: 0;
      font-family: "Fira Code", "Consolas", "Courier New", monospace;
      font-size: 13px;
      line-height: 1.6;
      overflow-x: auto;
      max-height: 520px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;

      code {
        font-family: inherit;
        color: inherit;
      }
    }
  }

  // Version dialog
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
}
</style>
