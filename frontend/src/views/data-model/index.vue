<template>
  <div class="model-page">
    <section class="metrics">
      <el-card v-for="item in metricCards" :key="item.label" shadow="never" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
        <div class="metric-note">{{ item.note }}</div>
      </el-card>
    </section>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <div class="title">模型设计</div>
            <div class="subtitle">管理模型分层、粒度、更新策略、上游依赖和字段结构</div>
          </div>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建模型</el-button>
        </div>
      </template>

      <div class="filters">
        <el-input v-model="filters.keyword" clearable :prefix-icon="Search" placeholder="模型名称、编码或表名" style="width: 240px" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.layer" clearable placeholder="全部分层" style="width: 120px" @change="search">
          <el-option v-for="layer in layers" :key="layer" :label="layer.toUpperCase()" :value="layer" />
        </el-select>
        <el-select v-model="filters.data_domain" clearable filterable placeholder="全部数据域" style="width: 160px" @change="onDomainFilterChange">
          <el-option v-for="item in dataDomains" :key="item.domain_code" :label="item.domain_name" :value="item.domain_name" />
        </el-select>
        <el-select v-model="filters.business_domain" clearable filterable placeholder="全部业务过程" style="width: 170px" @change="search">
          <el-option v-for="item in filteredProcessOptions" :key="item.domain_code" :label="item.domain_name" :value="item.domain_name" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
      </div>

      <el-table :data="models" v-loading="loading" border stripe>
        <el-table-column label="模型" min-width="210" fixed="left">
          <template #default="{ row }">
            <div class="model-cell">
              <el-button link type="primary" class="model-name" @click="openDetail(row)">{{ row.model_name }}</el-button>
              <code>{{ row.table_name }}</code>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分层" width="82" align="center">
          <template #default="{ row }"><el-tag :type="layerTag(row.layer)" effect="plain">{{ row.layer.toUpperCase() }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="data_domain" label="数据域" width="140" show-overflow-tooltip />
        <el-table-column prop="business_domain" label="业务过程" width="140" show-overflow-tooltip />
        <el-table-column prop="model_grain" label="模型粒度" min-width="230" show-overflow-tooltip>
          <template #default="{ row }">{{ row.model_grain || "待定义" }}</template>
        </el-table-column>
        <el-table-column label="更新策略" width="135">
          <template #default="{ row }">{{ strategyLabel(row.update_strategy) }}</template>
        </el-table-column>
        <el-table-column label="字段" width="76" align="center">
          <template #default="{ row }">{{ row.fields?.length || 0 }}</template>
        </el-table-column>
        <el-table-column label="来源" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_external" type="success" size="small">已同步</el-tag>
            <el-tag v-else type="info" size="small">手工设计</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="!row.is_external && row.status !== 'active'" link type="warning" @click="publishModel(row)">发布</el-button>
            <el-button link type="danger" @click="deleteModel(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="没有符合条件的模型" /></template>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="loadModels"
        @size-change="search"
        class="pagination"
      />
    </el-card>

    <el-drawer v-model="detailVisible" title="模型详情" size="680px">
      <template v-if="detail">
        <div class="detail-heading">
          <div>
            <h3>{{ detail.model_name }}</h3>
            <code>{{ detail.database }}.{{ detail.table_name }}</code>
          </div>
          <el-tag :type="layerTag(detail.layer)" effect="dark">{{ detail.layer.toUpperCase() }}</el-tag>
        </div>
        <el-descriptions :column="2" border class="detail-block">
          <el-descriptions-item label="数据域">{{ detail.data_domain || "-" }}</el-descriptions-item>
          <el-descriptions-item label="业务过程">{{ detail.business_domain || "-" }}</el-descriptions-item>
          <el-descriptions-item label="模型粒度" :span="2">{{ detail.model_grain || "待定义" }}</el-descriptions-item>
          <el-descriptions-item label="更新策略">{{ strategyLabel(detail.update_strategy) }}</el-descriptions-item>
          <el-descriptions-item label="版本">V{{ detail.current_version }}</el-descriptions-item>
          <el-descriptions-item label="说明" :span="2">{{ detail.description || "-" }}</el-descriptions-item>
        </el-descriptions>

        <h4>上游依赖</h4>
        <div v-if="detail.source_tables?.length" class="tag-list">
          <el-tag v-for="source in detail.source_tables" :key="source" effect="plain">{{ source }}</el-tag>
        </div>
        <el-empty v-else description="源表或静态模型，无已登记上游" :image-size="56" />

        <h4>字段设计（{{ detail.fields?.length || 0 }}）</h4>
        <el-table :data="detail.fields || []" border size="small" max-height="420">
          <el-table-column prop="field_name" label="字段" min-width="150" />
          <el-table-column prop="field_type" label="类型" width="140" />
          <el-table-column prop="field_comment" label="说明" min-width="170">
            <template #default="{ row }">{{ row.field_comment || "-" }}</template>
          </el-table-column>
          <el-table-column label="属性" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.is_primary_key" size="small">主键</el-tag>
              <el-tag v-if="row.is_partition" size="small" type="warning">分区</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>

    <el-dialog v-model="editorVisible" :title="isNew ? '新建模型' : '编辑模型'" width="920px" top="4vh" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
        <el-steps :active="activeTab === 'basic' ? 0 : 1" finish-status="success" simple class="editor-steps">
          <el-step title="1. 基本设计" />
          <el-step title="2. 字段设计" />
        </el-steps>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本设计" name="basic">
            <el-alert title="填写基本信息后，点击“下一步：字段设计”添加字段，字段会随模型一起保存。" type="info" :closable="false" show-icon class="editor-tip" />
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="模型名称" prop="model_name"><el-input v-model="form.model_name" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="分层" prop="layer"><el-select v-model="form.layer" :disabled="!isNew" style="width: 100%"><el-option v-for="layer in layers" :key="layer" :label="layer.toUpperCase()" :value="layer" /></el-select></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="数据库" prop="database"><el-input v-model="form.database" :disabled="!isNew" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="表名" prop="table_name"><el-input v-model="form.table_name" :disabled="!isNew" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="模型编码"><el-input v-model="form.model_code" :disabled="!isNew" placeholder="留空自动生成" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="数据域" prop="data_domain"><el-select v-model="form.data_domain" filterable style="width: 100%" @change="form.business_domain = ''"><el-option v-for="item in dataDomains" :key="item.domain_code" :label="item.domain_name" :value="item.domain_name" /></el-select></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="业务过程" prop="business_domain"><el-select v-model="form.business_domain" filterable style="width: 100%"><el-option v-for="item in editorProcessOptions" :key="item.domain_code" :label="item.domain_name" :value="item.domain_name" /></el-select></el-form-item></el-col>
              <el-col :span="16"><el-form-item label="模型粒度" prop="model_grain"><el-input v-model="form.model_grain" placeholder="例如：每个收费明细事件一条记录" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="更新策略" prop="update_strategy"><el-select v-model="form.update_strategy" style="width: 100%"><el-option v-for="item in strategies" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
              <el-col :span="24"><el-form-item label="上游表"><el-select v-model="form.source_tables" multiple filterable allow-create default-first-option style="width: 100%" placeholder="输入上游表名后回车" /></el-form-item></el-col>
              <el-col :span="24"><el-form-item label="模型说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item></el-col>
            </el-row>
          </el-tab-pane>
          <el-tab-pane :label="`字段设计（${form.fields.length}）`" name="fields">
            <div class="field-toolbar">
              <span>定义字段类型、主键和分区字段</span>
              <el-button type="primary" plain :icon="Plus" @click="addField">添加字段</el-button>
            </div>
            <el-table :data="form.fields" border max-height="430">
              <el-table-column type="index" label="#" width="48" />
              <el-table-column label="字段名" min-width="170"><template #default="{ row }"><el-input v-model="row.field_name" /></template></el-table-column>
              <el-table-column label="类型" width="170"><template #default="{ row }"><el-select v-model="row.field_type" filterable allow-create><el-option v-for="type in fieldTypes" :key="type" :label="type" :value="type" /></el-select></template></el-table-column>
              <el-table-column label="字段说明" min-width="180"><template #default="{ row }"><el-input v-model="row.field_comment" /></template></el-table-column>
              <el-table-column label="主键" width="68" align="center"><template #default="{ row }"><el-checkbox v-model="row.is_primary_key" /></template></el-table-column>
              <el-table-column label="分区" width="68" align="center"><template #default="{ row }"><el-checkbox v-model="row.is_partition" /></template></el-table-column>
              <el-table-column label="操作" width="70"><template #default="{ $index }"><el-button link type="danger" @click="form.fields.splice($index, 1)">删除</el-button></template></el-table-column>
              <template #empty>
                <el-empty description="还没有字段，请先添加模型字段" :image-size="64">
                  <el-button type="primary" :icon="Plus" @click="addField">添加第一个字段</el-button>
                </el-empty>
              </template>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button v-if="activeTab === 'fields'" @click="activeTab = 'basic'">上一步</el-button>
        <el-button v-if="activeTab === 'basic'" type="primary" @click="goToFields">下一步：字段设计</el-button>
        <el-button v-else type="primary" :loading="saving" @click="saveModel">保存模型</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { Plus, RefreshLeft, Search } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance, type TagProps } from "element-plus";
import { dataModelApi } from "@/api";

type TagType = TagProps["type"];
const layers = ["ods", "dim", "dwd", "dws", "ads"];
const strategies = [
  { label: "全量快照", value: "full_snapshot" }, { label: "增量追加", value: "incremental" },
  { label: "全量合并", value: "full_merge" }, { label: "分区覆盖", value: "partition_overwrite" },
  { label: "缓慢变化维 SCD2", value: "scd2" }, { label: "静态数据", value: "static" },
];
const fieldTypes = ["BIGINT", "INT", "DECIMAL(18,2)", "VARCHAR(255)", "STRING", "DATEV2", "DATETIMEV2", "BOOLEAN"];

const loading = ref(false), saving = ref(false), editorVisible = ref(false), detailVisible = ref(false);
const isNew = ref(false), activeTab = ref("basic"), selectedId = ref("");
const models = ref<any[]>([]), dataDomains = ref<any[]>([]), processes = ref<any[]>([]), detail = ref<any>(null);
const overview = ref<any>({ data_domains: 0, business_processes: 0, models: 0, external_models: 0, layers: {} });
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const filters = reactive({ keyword: "", layer: "", data_domain: "", business_domain: "" });
const formRef = ref<FormInstance>();
const emptyForm = () => ({ model_name: "", model_code: "", layer: "dwd", database: "dwd", table_name: "", data_domain: "", business_domain: "", model_grain: "", update_strategy: "partition_overwrite", source_tables: [] as string[], description: "", fields: [] as any[] });
const form = reactive(emptyForm());
const rules = {
  model_name: [{ required: true, message: "请输入模型名称", trigger: "blur" }],
  layer: [{ required: true, message: "请选择分层", trigger: "change" }],
  database: [{ required: true, message: "请输入数据库", trigger: "blur" }],
  table_name: [{ required: true, message: "请输入表名", trigger: "blur" }],
  data_domain: [{ required: true, message: "请选择数据域", trigger: "change" }],
  business_domain: [{ required: true, message: "请选择业务过程", trigger: "change" }],
  model_grain: [{ required: true, message: "请定义模型粒度", trigger: "blur" }],
  update_strategy: [{ required: true, message: "请选择更新策略", trigger: "change" }],
};

const filteredProcessOptions = computed(() => filters.data_domain ? processes.value.filter(item => item.data_domain === filters.data_domain) : processes.value);
const editorProcessOptions = computed(() => form.data_domain ? processes.value.filter(item => item.data_domain === form.data_domain) : processes.value);
const metricCards = computed(() => [
  { label: "数据域", value: overview.value.data_domains, note: "责任边界" },
  { label: "业务过程", value: overview.value.business_processes, note: "可度量业务活动" },
  { label: "模型总数", value: overview.value.models, note: `${overview.value.external_models} 个已同步物理表` },
  { label: "分层分布", value: Object.keys(overview.value.layers || {}).length, note: layers.map(layer => `${layer.toUpperCase()} ${overview.value.layers?.[layer.toUpperCase()] || 0}`).join(" · ") },
]);

async function loadModels() {
  loading.value = true;
  try {
    const res = await dataModelApi.list({ page: pagination.page, page_size: pagination.page_size, ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value)) });
    models.value = res.items || [];
    pagination.total = res.total || 0;
  } finally { loading.value = false; }
}
async function loadReferenceData() {
  const [domains, processRows, stats] = await Promise.all([dataModelApi.dataDomains(), dataModelApi.businessDomains(), dataModelApi.overview()]);
  dataDomains.value = domains || []; processes.value = processRows || []; overview.value = stats || overview.value;
}
function search() { pagination.page = 1; loadModels(); }
function resetFilters() { Object.assign(filters, { keyword: "", layer: "", data_domain: "", business_domain: "" }); search(); }
function onDomainFilterChange() { filters.business_domain = ""; search(); }
function openCreate() { isNew.value = true; selectedId.value = ""; Object.assign(form, emptyForm()); activeTab.value = "basic"; editorVisible.value = true; }
async function openEdit(row: any) { isNew.value = false; selectedId.value = row.id; const data = await dataModelApi.detail(row.id); Object.assign(form, emptyForm(), data, { source_tables: data.source_tables || [], fields: (data.fields || []).map((field: any) => ({ ...field })) }); activeTab.value = "basic"; editorVisible.value = true; }
async function openDetail(row: any) { detail.value = await dataModelApi.detail(row.id); detailVisible.value = true; }
function addField() { form.fields.push({ field_name: "", field_type: "VARCHAR(255)", field_comment: "", is_primary_key: false, is_partition: false, default_value: null, sort_order: form.fields.length }); }

async function goToFields() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (valid) activeTab.value = "fields";
}

async function saveModel() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false); if (!valid) { activeTab.value = "basic"; return; }
  if (!form.fields.length) { activeTab.value = "fields"; ElMessage.warning("请至少添加一个模型字段"); return; }
  if (form.fields.some(field => !field.field_name || !field.field_type)) { activeTab.value = "fields"; ElMessage.warning("请补全字段名称和类型"); return; }
  saving.value = true;
  try {
    const payload = { ...form, model_code: form.model_code || undefined, fields: form.fields.map((field, index) => ({ ...field, sort_order: index })) };
    if (isNew.value) await dataModelApi.create(payload); else await dataModelApi.update(selectedId.value, payload);
    ElMessage.success("模型设计已保存"); editorVisible.value = false; await Promise.all([loadModels(), loadReferenceData()]);
  } finally { saving.value = false; }
}

async function publishModel(row: any) {
  await ElMessageBox.confirm(`确认发布“${row.model_name}”并在 Doris 创建 ${row.database}.${row.table_name}？`, "发布确认", { type: "warning" });
  await dataModelApi.publish(row.id); ElMessage.success("模型已发布"); await loadModels();
}
async function deleteModel(row: any) {
  const message = row.is_external ? `确认删除“${row.model_name}”的模型设计记录？Doris 物理表不会被删除。` : `确认删除“${row.model_name}”？手工模型对应的 Doris 表也会被删除。`;
  await ElMessageBox.confirm(message, "删除确认", { type: "warning" });
  await dataModelApi.delete(row.id); ElMessage.success("模型已删除"); await Promise.all([loadModels(), loadReferenceData()]);
}
function layerTag(layer: string): TagType { return ({ ods: "info", dim: "success", dwd: "primary", dws: "warning", ads: "danger" } as Record<string, TagType>)[layer] || "info"; }
function strategyLabel(value: string) { return strategies.find(item => item.value === value)?.label || value || "待定义"; }
watch(() => form.layer, value => { if (isNew.value) form.database = value; });
onMounted(async () => { await Promise.all([loadModels(), loadReferenceData()]); });
</script>

<style lang="scss" scoped>
.model-page { display: flex; flex-direction: column; gap: 16px; }
.metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.metric-card { border-radius: 10px; }
.metric-label { color: var(--el-text-color-secondary); font-size: 13px; }
.metric-value { margin: 8px 0 4px; font-size: 28px; font-weight: 700; color: var(--el-text-color-primary); }
.metric-note { min-height: 18px; color: var(--el-text-color-secondary); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-header, .filters, .detail-heading, .field-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.filters { justify-content: flex-start; flex-wrap: wrap; margin-bottom: 16px; }
.title { font-size: 16px; font-weight: 600; }
.subtitle { margin-top: 4px; font-size: 13px; color: var(--el-text-color-secondary); }
.model-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; }
.model-name { padding: 0; font-weight: 600; }
code { color: var(--el-text-color-secondary); font-size: 12px; }
.pagination { margin-top: 16px; justify-content: flex-end; }
.detail-heading { margin-bottom: 20px; }
.detail-heading h3 { margin: 0 0 6px; font-size: 20px; }
.detail-block { margin-bottom: 22px; }
h4 { margin: 22px 0 10px; }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.field-toolbar { margin-bottom: 12px; color: var(--el-text-color-secondary); }
.editor-steps { margin-bottom: 12px; }
.editor-tip { margin-bottom: 18px; }
@media (max-width: 1100px) { .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
