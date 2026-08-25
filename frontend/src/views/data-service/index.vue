<template>
  <div class="service-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <div>
            <div class="page-title">服务目录</div>
            <div class="page-subtitle">将物理表或只读 SQL 发布为统一、可测试的数据 API</div>
          </div>
          <el-button type="primary" :icon="Plus" @click="handleAdd()">新建服务</el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width: 140px" @change="fetchList">
          <el-option label="草稿" value="draft" />
          <el-option label="已发布" value="published" />
          <el-option label="已停用" value="offline" />
        </el-select>
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
        <span class="service-count">共 {{ total }} 个服务</span>
      </div>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column label="服务" min-width="210">
          <template #default="{ row }">
            <div class="service-name">{{ row.api_name }}</div>
            <div class="secondary">{{ row.service_code }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="serviceTypeTag(row.service_type)" effect="plain">
              {{ serviceTypeLabel(row.service_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数据来源" min-width="190">
          <template #default="{ row }">
            <div>{{ row.service_type === "metric" ? `${row.metric_ids?.length || 0} 个指标` : (row.datasource_name || "历史 Doris 配置") }}</div>
            <div class="secondary">{{ row.service_type === "metric" ? (row.time_dimension || "无时间维度") : ([row.database, row.table_name].filter(Boolean).join(".") || "-") }}</div>
          </template>
        </el-table-column>
        <el-table-column label="调用地址" min-width="250">
          <template #default="{ row }">
            <el-tag size="small" :type="row.method === 'GET' ? 'success' : 'primary'">{{ row.method }}</el-tag>
            <code>{{ row.api_path }}</code>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="call_count" label="调用次数" width="100" align="right" />
        <el-table-column label="操作" width="400" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" @click="handleTest(row)">测试</el-button>
            <el-button v-if="row.status !== 'published'" link type="primary" @click="changeStatus(row, 'published')">发布</el-button>
            <el-button v-else link type="warning" @click="changeStatus(row, 'offline')">停用</el-button>
            <el-button v-if="row.status === 'published'" link type="primary" @click="openKeyDialog(row)">凭证</el-button>
            <el-button v-if="row.status === 'published'" link type="primary" @click="openDocDialog(row)">文档</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
        :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="fetchList" @current-change="fetchList" /></div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="isEdit ? '编辑数据服务' : '新建数据服务'" size="min(980px, 92vw)" @closed="resetForm">
      <el-steps :active="activeStep" finish-status="success" align-center class="steps">
        <el-step title="基本信息" />
        <el-step title="数据配置" />
        <el-step title="参数与发布" />
      </el-steps>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="service-form">
        <section v-show="activeStep === 0" class="step-panel">
          <el-alert title="支持物理表、自定义 SQL 和统一指标三种数据服务。" type="info" show-icon :closable="false" />
          <el-row :gutter="18">
            <el-col :span="12"><el-form-item label="服务名称" prop="api_name"><el-input v-model="form.api_name" placeholder="例如：用户订单查询" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="服务编码" prop="service_code"><el-input v-model="form.service_code" :disabled="isEdit" placeholder="例如：user_orders" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="服务类型" prop="service_type"><el-radio-group v-model="form.service_type" @change="onTypeChange"><el-radio-button value="table">物理表</el-radio-button><el-radio-button value="custom_sql">自定义 SQL</el-radio-button><el-radio-button value="metric">指标</el-radio-button></el-radio-group></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="请求方式"><el-radio-group v-model="form.method"><el-radio-button value="GET">GET</el-radio-button><el-radio-button value="POST">POST</el-radio-button></el-radio-group></el-form-item></el-col>
            <el-col :span="24"><el-form-item label="服务描述"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="说明接口用途和业务口径" /></el-form-item></el-col>
            <el-col :span="24"><el-form-item label="调用地址"><el-input :model-value="servicePath" readonly><template #prepend>{{ form.method }}</template></el-input></el-form-item></el-col>
          </el-row>
        </section>

        <section v-show="activeStep === 1" class="step-panel">
          <el-row v-if="form.service_type !== 'metric'" :gutter="18">
            <el-col :span="12"><el-form-item label="数据源" prop="datasource_id"><el-select v-model="form.datasource_id" filterable placeholder="选择真实数据源" style="width:100%" @change="onDatasourceChange"><el-option v-for="item in datasourceOptions" :key="item.id" :label="item.source_name" :value="item.id"><span>{{ item.source_name }}</span><span class="option-meta">{{ item.source_type }}</span></el-option></el-select></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="数据库" prop="database"><el-select v-model="form.database" filterable placeholder="选择数据库" style="width:100%" :loading="databaseLoading" @change="loadTables"><el-option v-for="item in databaseOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
          </el-row>

          <template v-if="form.service_type === 'table'">
            <el-form-item label="物理表" prop="table_name"><el-select v-model="form.table_name" filterable placeholder="选择物理表" style="width:100%" :loading="tableLoading" @change="loadColumns"><el-option v-for="item in tableOptions" :key="item.name" :label="item.name" :value="item.name" /></el-select></el-form-item>
            <el-form-item label="返回字段" prop="selected_fields"><el-checkbox-group v-model="form.selected_fields" class="field-grid"><el-checkbox v-for="item in columnOptions" :key="item.field" :value="item.field"><span>{{ item.field }}</span><small>{{ item.type }}</small></el-checkbox></el-checkbox-group><el-empty v-if="!columnOptions.length" description="选择物理表后自动加载字段" :image-size="48" /></el-form-item>
            <el-form-item label="过滤字段"><el-select v-model="form.filter_names" multiple filterable collapse-tags placeholder="选择允许调用方传入的过滤字段" style="width:100%"><el-option v-for="item in columnOptions" :key="item.field" :label="`${item.field} (${item.type})`" :value="item.field" /></el-select></el-form-item>
          </template>
          <template v-else-if="form.service_type === 'custom_sql'">
            <el-form-item label="SQL 模板" prop="sql_template"><el-input v-model="form.sql_template" type="textarea" :rows="13" placeholder="SELECT * FROM orders WHERE user_id = ${user_id}" /></el-form-item>
            <el-alert title="仅允许单条 SELECT/SHOW/DESC/WITH 查询，参数统一使用 ${param} 格式。" type="warning" :closable="false" show-icon />
          </template>
          <template v-else>
            <el-form-item label="指标" prop="metric_ids">
              <el-select v-model="form.metric_ids" multiple filterable collapse-tags placeholder="选择一个或多个同 Cube 指标" style="width:100%" @change="onMetricsChange">
                <el-option v-for="item in metricOptions" :key="item.id" :label="`${item.metric_name} (${item.metric_code})`" :value="item.id"><span>{{ item.metric_name }}</span><span class="option-meta">{{ item.cube_name }} · {{ item.metric_type }}</span></el-option>
              </el-select>
            </el-form-item>
            <el-alert v-if="selectedMetricCubes.length > 1" title="所选指标属于不同 Cube，请调整为同一个 Cube。" type="error" :closable="false" show-icon />
            <el-form-item label="查询维度"><el-select v-model="form.metric_dimensions" multiple filterable collapse-tags placeholder="选择返回维度" style="width:100%"><el-option v-for="item in availableMetricDimensions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
            <el-row :gutter="18">
              <el-col :span="12"><el-form-item label="时间维度"><el-select v-model="form.time_dimension" clearable filterable placeholder="可选" style="width:100%"><el-option v-for="item in availableMetricDimensions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="默认粒度"><el-select v-model="form.default_granularity" :disabled="!form.time_dimension" style="width:100%"><el-option label="日" value="day" /><el-option label="周" value="week" /><el-option label="月" value="month" /><el-option label="季度" value="quarter" /><el-option label="年" value="year" /></el-select></el-form-item></el-col>
            </el-row>
            <el-form-item label="过滤维度"><el-select v-model="form.metric_filter_names" multiple filterable collapse-tags placeholder="允许调用方传入的过滤维度" style="width:100%"><el-option v-for="item in availableMetricDimensions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
          </template>
        </section>

        <section v-show="activeStep === 2" class="step-panel">
          <el-form-item label="最大返回行数"><el-input-number v-model="form.max_rows" :min="1" :max="10000" :step="100" /></el-form-item>
          <el-form-item label="查询缓存"><el-switch v-model="form.cache_enabled" active-text="启用 Redis 缓存" /></el-form-item>
          <el-form-item v-if="form.cache_enabled" label="缓存时间"><el-input-number v-model="form.cache_ttl" :min="30" :max="86400" :step="60" /><span class="unit-text">秒</span></el-form-item>
          <el-form-item v-if="form.service_type === 'custom_sql'" label="请求参数">
            <div class="param-list">
              <div v-for="(param, index) in form.parameters" :key="index" class="param-row">
                <el-input v-model="param.name" placeholder="参数名" />
                <el-select v-model="param.type"><el-option v-for="type in parameterTypes" :key="type" :label="type" :value="type" /></el-select>
                <el-checkbox v-model="param.required">必填</el-checkbox>
                <el-button link type="danger" :icon="Delete" @click="form.parameters.splice(index, 1)" />
              </div>
              <el-button link type="primary" :icon="Plus" @click="form.parameters.push({ name: '', type: 'string', required: false })">添加参数</el-button>
            </div>
          </el-form-item>
          <el-descriptions title="发布预览" :column="2" border>
            <el-descriptions-item label="调用地址">{{ servicePath }}</el-descriptions-item>
            <el-descriptions-item label="请求方式">{{ form.method }}</el-descriptions-item>
            <el-descriptions-item label="数据来源">{{ form.service_type === "metric" ? `${form.metric_ids.length} 个指标` : `${selectedDatasourceName} / ${form.database || "-"}` }}</el-descriptions-item>
            <el-descriptions-item label="最大行数">{{ form.max_rows }}</el-descriptions-item>
            <el-descriptions-item label="查询预览" :span="2"><pre class="sql-preview">{{ queryPreview }}</pre></el-descriptions-item>
          </el-descriptions>
        </section>
      </el-form>

      <template #footer>
        <div class="drawer-footer">
          <el-button @click="drawerVisible = false">取消</el-button>
          <div><el-button v-if="activeStep > 0" @click="activeStep--">上一步</el-button><el-button v-if="activeStep < 2" type="primary" @click="nextStep">下一步</el-button><el-button v-else type="primary" :loading="submitting" @click="handleSubmit">保存草稿</el-button></div>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="testVisible" title="在线测试" width="860px">
      <div v-if="currentApi">
        <div class="test-path"><el-tag :type="currentApi.method === 'GET' ? 'success' : 'primary'">{{ currentApi.method }}</el-tag><code>{{ currentApi.api_path }}</code></div>
        <el-form label-width="130px" class="test-form">
          <el-form-item v-for="param in testParams" :key="param.name" :label="param.name"><el-input v-model="param.value" :placeholder="`${param.type}${param.required ? ' · 必填' : ' · 可选'}`" /></el-form-item>
        </el-form>
        <el-divider />
        <div v-if="testResult" class="result-meta"><el-tag>{{ testResult.row_count }} 行</el-tag><el-tag type="success">{{ testResult.elapsed_ms }} ms</el-tag><el-tag v-if="testResult.truncated" type="warning">已截断</el-tag></div>
        <el-table v-if="testResult?.rows?.length" :data="testResult.rows" border max-height="380"><el-table-column v-for="column in testResult.columns" :key="column" :prop="column" :label="column" min-width="130" show-overflow-tooltip /></el-table>
        <el-empty v-else :description="testResult ? '查询结果为空' : '填写参数后执行测试'" :image-size="54" />
      </div>
      <template #footer><el-button @click="testVisible = false">关闭</el-button><el-button type="primary" :loading="testing" @click="executeTest">执行测试</el-button></template>
    </el-dialog>

    <el-dialog v-model="keyDialogVisible" title="外部调用凭证" width="720px">
      <el-alert v-if="createdAppKey" title="AppKey 只展示一次，请立即复制并妥善保存。" type="warning" :closable="false" show-icon>
        <template #default><div class="created-key"><code>{{ createdAppKey }}</code><el-button size="small" @click="copyAppKey">复制</el-button></div></template>
      </el-alert>
      <div class="key-create"><el-input v-model="newKeyName" placeholder="凭证名称，例如：经营驾驶舱" /><el-button type="primary" :disabled="newKeyName.trim().length < 2" @click="createKey">创建 AppKey</el-button></div>
      <el-table :data="appKeys" border>
        <el-table-column prop="key_name" label="名称" />
        <el-table-column prop="key_prefix" label="Key 前缀" />
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === "active" ? "有效" : "已撤销" }}</el-tag></template></el-table-column>
        <el-table-column label="最近使用" width="180"><template #default="{ row }">{{ row.last_used_at ? new Date(row.last_used_at).toLocaleString("zh-CN", { hour12: false }) : "-" }}</template></el-table-column>
        <el-table-column label="操作" width="90"><template #default="{ row }"><el-button v-if="row.status === 'active'" link type="danger" @click="revokeKey(row)">撤销</el-button></template></el-table-column>
      </el-table>
      <el-alert class="key-usage" type="info" :closable="false"><template #default>外部调用时添加请求头：<code>X-API-Key: dmk_xxx</code></template></el-alert>
    </el-dialog>

    <el-dialog v-model="docVisible" title="接口文档" width="min(920px, 94vw)" top="5vh">
      <div v-if="docApi" class="api-doc">
        <div class="doc-header">
          <div><h2>{{ docApi.api_name }}</h2><p>{{ docApi.description || "暂无服务说明" }}</p></div>
          <el-tag type="success">已发布</el-tag>
        </div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="服务编码">{{ docApi.service_code }}</el-descriptions-item>
          <el-descriptions-item label="服务类型">{{ serviceTypeLabel(docApi.service_type) }}</el-descriptions-item>
          <el-descriptions-item label="请求方式"><el-tag size="small">{{ docApi.method }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="鉴权方式">X-API-Key</el-descriptions-item>
          <el-descriptions-item label="请求地址" :span="2"><code>{{ externalApiUrl(docApi) }}</code></el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">{{ formatDocTime(docApi.updated_at) }}</el-descriptions-item>
        </el-descriptions>

        <h3>请求参数</h3>
        <el-table :data="docApi.parameters || []" border size="small">
          <el-table-column prop="name" label="参数名" min-width="160" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column label="是否必填" width="100"><template #default="{ row }">{{ row.required ? "是" : "否" }}</template></el-table-column>
          <template #empty><el-empty description="无请求参数" :image-size="48" /></template>
        </el-table>

        <h3>返回字段</h3>
        <div v-if="docResponseFields.length" class="response-fields"><el-tag v-for="field in docResponseFields" :key="field" effect="plain">{{ field }}</el-tag></div>
        <el-empty v-else description="返回字段由查询结果动态确定" :image-size="48" />

        <h3>curl 示例</h3>
        <div class="code-block"><el-button size="small" @click="copyText(docSamples.curl)">复制</el-button><pre>{{ docSamples.curl }}</pre></div>
        <h3>Python 示例</h3>
        <div class="code-block"><el-button size="small" @click="copyText(docSamples.python)">复制</el-button><pre>{{ docSamples.python }}</pre></div>

        <el-alert title="文档中的 YOUR_APP_KEY 是占位符，请替换为服务凭证页面生成的 AppKey。" type="warning" :closable="false" show-icon />
      </div>
      <template #footer>
        <el-button @click="downloadMarkdown">导出 Markdown</el-button>
        <el-button @click="downloadOpenApi">导出 OpenAPI JSON</el-button>
        <el-button type="primary" @click="docVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { Delete, Plus, Refresh } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { datasourceApi, dataServiceApi, metricDefinitionApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";
interface Parameter { name: string; type: string; required: boolean; value?: string }
interface ServiceForm { api_name: string; service_code: string; service_type: "table" | "custom_sql" | "metric"; method: "GET" | "POST"; description: string; datasource_id: string; database: string; table_name: string; selected_fields: string[]; filter_names: string[]; sql_template: string; parameters: Parameter[]; metric_ids: string[]; metric_dimensions: string[]; time_dimension: string; default_granularity: string; metric_filter_names: string[]; max_rows: number; cache_enabled: boolean; cache_ttl: number }

const loading = ref(false), submitting = ref(false), databaseLoading = ref(false), tableLoading = ref(false), testing = ref(false);
const tableData = ref<any[]>([]), datasourceOptions = ref<any[]>([]), databaseOptions = ref<string[]>([]), tableOptions = ref<any[]>([]), columnOptions = ref<any[]>([]), metricOptions = ref<any[]>([]);
const page = ref(1), pageSize = ref(10), total = ref(0), statusFilter = ref("");
const drawerVisible = ref(false), isEdit = ref(false), editId = ref(""), activeStep = ref(0), formRef = ref<FormInstance>();
const testVisible = ref(false), currentApi = ref<any>(), testParams = ref<Parameter[]>([]), testResult = ref<any>();
const keyDialogVisible = ref(false), keyService = ref<any>(), appKeys = ref<any[]>([]), newKeyName = ref(""), createdAppKey = ref("");
const docVisible = ref(false), docApi = ref<any>();
const parameterTypes = ["string", "integer", "float", "boolean", "date", "array"];
const emptyForm = (): ServiceForm => ({ api_name: "", service_code: "", service_type: "table", method: "GET", description: "", datasource_id: "", database: "", table_name: "", selected_fields: [], filter_names: [], sql_template: "", parameters: [], metric_ids: [], metric_dimensions: [], time_dimension: "", default_granularity: "day", metric_filter_names: [], max_rows: 1000, cache_enabled: false, cache_ttl: 300 });
const form = reactive<ServiceForm>(emptyForm());
const rules = {
  api_name: [{ required: true, message: "请输入服务名称", trigger: "blur" }],
  service_code: [{ required: true, pattern: /^[a-z][a-z0-9_]*$/, message: "以小写字母开头，只能包含小写字母、数字和下划线", trigger: "blur" }],
  datasource_id: [{ required: true, message: "请选择数据源", trigger: "change" }],
  database: [{ required: true, message: "请选择数据库", trigger: "change" }],
  table_name: [{ required: true, message: "请选择物理表", trigger: "change" }],
  selected_fields: [{ type: "array", min: 1, message: "至少选择一个返回字段", trigger: "change" }],
  sql_template: [{ validator: (_: any, value: string, callback: (error?: Error) => void) => form.service_type === "custom_sql" && !value.trim() ? callback(new Error("请输入 SQL 模板")) : callback(), trigger: "blur" }],
  metric_ids: [{ type: "array", min: 1, message: "至少选择一个指标", trigger: "change" }],
};

const servicePath = computed(() => `/open-api/v1/${form.service_code || "service_code"}`);
const selectedDatasourceName = computed(() => datasourceOptions.value.find((item) => item.id === form.datasource_id)?.source_name || "-");
const selectedMetrics = computed(() => form.metric_ids.map((id) => metricOptions.value.find((item) => item.id === id)).filter(Boolean));
const selectedMetricCubes = computed(() => [...new Set(selectedMetrics.value.map((item) => item.cube_name).filter(Boolean))]);
const availableMetricDimensions = computed(() => [...new Set(selectedMetrics.value.flatMap((item) => [...(item.dimensions || []), item.default_time_dimension].filter(Boolean)))].sort());
const queryPreview = computed(() => {
  if (form.service_type === "metric") return JSON.stringify({ measures: selectedMetrics.value.map((item) => item.cube_measure), dimensions: form.metric_dimensions, timeDimension: form.time_dimension || undefined, granularity: form.time_dimension ? form.default_granularity : undefined, filters: form.metric_filter_names, limit: form.max_rows }, null, 2);
  if (form.service_type === "custom_sql") return form.sql_template || "-- 尚未配置 SQL";
  if (!form.table_name || !form.selected_fields.length) return "-- 选择物理表和返回字段后生成";
  const filters = form.filter_names.map((name) => `${name} = \${${name}}`).join(" AND ");
  return `SELECT ${form.selected_fields.join(", ")}\nFROM ${form.table_name}${filters ? `\nWHERE ${filters}` : ""}\nLIMIT ${form.max_rows}`;
});
const docResponseFields = computed(() => {
  if (!docApi.value) return [];
  if (docApi.value.service_type === "table") return docApi.value.selected_fields || [];
  if (docApi.value.service_type === "metric") {
    const measures = (docApi.value.metric_ids || []).map((id: string) => metricOptions.value.find((item) => item.id === id)?.cube_measure).filter(Boolean);
    return [...(docApi.value.metric_dimensions || []), ...measures];
  }
  return [];
});
const docSamples = computed(() => buildSamples(docApi.value));

function statusType(status: string): TagType { return status === "published" || status === "active" ? "success" : status === "draft" ? "info" : "warning"; }
function statusLabel(status: string) { return ({ draft: "草稿", published: "已发布", offline: "已停用", active: "已发布" } as Record<string, string>)[status] || status; }
function serviceTypeLabel(type: string) { return ({ table: "物理表", custom_sql: "自定义 SQL", metric: "指标服务" } as Record<string, string>)[type] || type; }
function serviceTypeTag(type: string): TagType { return type === "table" ? "primary" : type === "metric" ? "success" : "warning"; }
function columnType(name: string) { const raw = String(columnOptions.value.find((item) => item.field === name)?.type || "").toLowerCase(); if (raw.includes("int")) return "integer"; if (/decimal|double|float|numeric/.test(raw)) return "float"; if (raw.includes("bool")) return "boolean"; if (/date|time/.test(raw)) return "date"; return "string"; }

async function fetchList() { loading.value = true; try { const res: any = await dataServiceApi.list({ page: page.value, page_size: pageSize.value, status: statusFilter.value || undefined }); tableData.value = res.items || []; total.value = res.total || 0; } finally { loading.value = false; } }
async function loadDatasources() { const res: any = await datasourceApi.list({ page: 1, page_size: 100, status: "active" }); datasourceOptions.value = res.items || []; }
async function loadMetrics() { const res: any = await metricDefinitionApi.list({ page: 1, page_size: 100 }); metricOptions.value = (res.items || []).filter((item: any) => item.cube_measure); }
async function onDatasourceChange(reset = true) { if (reset) { form.database = ""; form.table_name = ""; form.selected_fields = []; form.filter_names = []; } databaseOptions.value = []; tableOptions.value = []; columnOptions.value = []; if (!form.datasource_id) return; databaseLoading.value = true; try { databaseOptions.value = await datasourceApi.listDatabases(form.datasource_id) as any || []; } finally { databaseLoading.value = false; } }
async function loadTables(reset = true) { if (reset) { form.table_name = ""; form.selected_fields = []; form.filter_names = []; } tableOptions.value = []; columnOptions.value = []; if (!form.datasource_id || !form.database) return; tableLoading.value = true; try { tableOptions.value = await datasourceApi.getTables(form.datasource_id, undefined, form.database) as any || []; } finally { tableLoading.value = false; } }
async function loadColumns(reset = true) { if (reset) { form.selected_fields = []; form.filter_names = []; } columnOptions.value = []; if (!form.datasource_id || !form.table_name) return; columnOptions.value = await datasourceApi.getColumns(form.datasource_id, form.table_name, undefined, form.database) as any || []; if (reset) form.selected_fields = columnOptions.value.map((item) => item.field); }

function onTypeChange() { form.table_name = ""; form.selected_fields = []; form.filter_names = []; form.sql_template = ""; form.parameters = []; form.metric_ids = []; form.metric_dimensions = []; form.metric_filter_names = []; form.time_dimension = ""; }
function onMetricsChange() { const allowed = new Set(availableMetricDimensions.value); form.metric_dimensions = form.metric_dimensions.filter((item) => allowed.has(item)); form.metric_filter_names = form.metric_filter_names.filter((item) => allowed.has(item)); if (form.time_dimension && !allowed.has(form.time_dimension)) form.time_dimension = ""; if (!form.time_dimension) form.time_dimension = selectedMetrics.value.find((item) => item.default_time_dimension)?.default_time_dimension || ""; }
function handleAdd() { Object.assign(form, emptyForm()); isEdit.value = false; activeStep.value = 0; drawerVisible.value = true; }
async function handleEdit(row: any) { const detail: any = await dataServiceApi.detail(row.id); Object.assign(form, emptyForm(), { ...detail, filter_names: detail.service_type === "table" ? (detail.filter_fields || []).map((item: any) => item.field) : [], metric_filter_names: detail.service_type === "metric" ? (detail.filter_fields || []).map((item: any) => item.member || item.field) : [], parameters: (detail.parameters || []).map((item: any) => ({ ...item })) }); isEdit.value = true; editId.value = row.id; activeStep.value = 0; drawerVisible.value = true; if (form.datasource_id) { await onDatasourceChange(false); const database = detail.database; form.database = database; await loadTables(false); form.table_name = detail.table_name || ""; if (form.table_name) await loadColumns(false); form.selected_fields = detail.selected_fields || []; form.filter_names = (detail.filter_fields || []).map((item: any) => item.field); } }
function resetForm() { formRef.value?.clearValidate(); Object.assign(form, emptyForm()); databaseOptions.value = []; tableOptions.value = []; columnOptions.value = []; }
async function nextStep() { if (!formRef.value) return; const fields = activeStep.value === 0 ? ["api_name", "service_code"] : form.service_type === "table" ? ["datasource_id", "database", "table_name", "selected_fields"] : form.service_type === "custom_sql" ? ["datasource_id", "database", "sql_template"] : ["metric_ids"]; try { await formRef.value.validateField(fields); if (activeStep.value === 1 && form.service_type === "metric" && selectedMetricCubes.value.length > 1) { ElMessage.warning("同一服务只能选择同一个 Cube 下的指标"); return; } activeStep.value += 1; } catch { /* validation message is shown by the form */ } }

function payload() { const tableParameters = form.filter_names.map((name) => ({ name, type: columnType(name), required: false })); const metricParameters = [...form.metric_filter_names.map((name) => ({ name, type: "string", required: false })), ...(form.time_dimension ? [{ name: "start_date", type: "date", required: false }, { name: "end_date", type: "date", required: false }, { name: "granularity", type: "string", required: false }] : [])]; return { api_name: form.api_name, service_code: form.service_code, service_type: form.service_type, method: form.method, description: form.description, datasource_id: form.service_type === "metric" ? null : form.datasource_id, database: form.service_type === "metric" ? "" : form.database, table_name: form.service_type === "table" ? form.table_name : null, selected_fields: form.service_type === "table" ? form.selected_fields : [], filter_fields: form.service_type === "table" ? form.filter_names.map((name) => ({ field: name, parameter: name, operator: "eq" })) : form.service_type === "metric" ? form.metric_filter_names.map((name) => ({ member: name, parameter: name, operator: "equals" })) : [], sql_template: form.service_type === "custom_sql" ? form.sql_template : "", parameters: form.service_type === "table" ? tableParameters : form.service_type === "metric" ? metricParameters : form.parameters.filter((item) => item.name.trim()).map(({ value, ...item }) => item), metric_ids: form.service_type === "metric" ? form.metric_ids : [], metric_dimensions: form.service_type === "metric" ? form.metric_dimensions : [], time_dimension: form.service_type === "metric" ? form.time_dimension : null, default_granularity: form.default_granularity, max_rows: form.max_rows, cache_enabled: form.cache_enabled, cache_ttl: form.cache_ttl, api_path: servicePath.value }; }
async function handleSubmit() { if (!formRef.value) return; try { await formRef.value.validate(); submitting.value = true; if (isEdit.value) await dataServiceApi.update(editId.value, payload()); else await dataServiceApi.create(payload()); ElMessage.success("草稿已保存"); drawerVisible.value = false; await fetchList(); } finally { submitting.value = false; } }
async function changeStatus(row: any, status: "published" | "offline") { if (status === "published") await dataServiceApi.publish(row.id); else await dataServiceApi.offline(row.id); ElMessage.success(status === "published" ? "发布成功" : "服务已停用"); await fetchList(); }
async function handleDelete(row: any) { try { await ElMessageBox.confirm(`确认删除数据服务“${row.api_name}”？`, "删除确认", { type: "warning" }); await dataServiceApi.delete(row.id); ElMessage.success("删除成功"); await fetchList(); } catch { /* cancelled */ } }

function handleTest(row: any) { currentApi.value = row; testParams.value = (row.parameters || []).map((item: any) => ({ ...item, value: "" })); testResult.value = undefined; testVisible.value = true; }
async function executeTest() { if (!currentApi.value) return; const missing = testParams.value.filter((item) => item.required && !item.value); if (missing.length) { ElMessage.warning(`请填写必填参数：${missing.map((item) => item.name).join("、")}`); return; } const params: Record<string, any> = {}; testParams.value.forEach((item) => { if (item.value !== "" && item.value !== undefined) params[item.name] = item.value; }); testing.value = true; try { testResult.value = await dataServiceApi.execute(currentApi.value.id, params); ElMessage.success("测试执行成功"); } finally { testing.value = false; } }

async function openKeyDialog(row: any) { keyService.value = row; createdAppKey.value = ""; newKeyName.value = ""; keyDialogVisible.value = true; appKeys.value = await dataServiceApi.appKeys(row.id) as any || []; }
async function createKey() { if (!keyService.value) return; const result: any = await dataServiceApi.createAppKey(keyService.value.id, { key_name: newKeyName.value.trim() }); createdAppKey.value = result.app_key; newKeyName.value = ""; appKeys.value = await dataServiceApi.appKeys(keyService.value.id) as any || []; }
async function revokeKey(row: any) { if (!keyService.value) return; await dataServiceApi.revokeAppKey(keyService.value.id, row.id); ElMessage.success("AppKey 已撤销"); appKeys.value = await dataServiceApi.appKeys(keyService.value.id) as any || []; }
async function copyAppKey() { await navigator.clipboard.writeText(createdAppKey.value); ElMessage.success("AppKey 已复制"); }

async function openDocDialog(row: any) { docApi.value = await dataServiceApi.detail(row.id); docVisible.value = true; }
function externalApiUrl(api: any) { return `${window.location.origin}/api/v1${api?.api_path || ""}`; }
function formatDocTime(value?: string) { return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"; }
function exampleValue(type: string) { if (["integer", "int", "float", "number"].includes(type)) return 1; if (["boolean", "bool"].includes(type)) return true; if (["array", "list"].includes(type)) return ["value1", "value2"]; if (type === "date") return "2026-01-01"; return "example"; }
function buildSamples(api: any) {
  if (!api) return { curl: "", python: "" };
  const params = Object.fromEntries((api.parameters || []).map((item: any) => [item.name, exampleValue(item.type)]));
  const url = externalApiUrl(api);
  if (api.method === "GET") {
    const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, Array.isArray(value) ? value.join(",") : String(value)])).toString();
    const fullUrl = query ? `${url}?${query}` : url;
    return {
      curl: `curl "${fullUrl}" \\\n  -H "X-API-Key: YOUR_APP_KEY"`,
      python: `import requests\n\nurl = "${url}"\nheaders = {"X-API-Key": "YOUR_APP_KEY"}\nparams = ${JSON.stringify(params, null, 4)}\n\nresponse = requests.get(url, headers=headers, params=params)\nprint(response.json())`,
    };
  }
  return {
    curl: `curl -X POST "${url}" \\\n  -H "Content-Type: application/json" \\\n  -H "X-API-Key: YOUR_APP_KEY" \\\n  -d '${JSON.stringify({ params }, null, 2)}'`,
    python: `import requests\n\nurl = "${url}"\nheaders = {"X-API-Key": "YOUR_APP_KEY"}\nbody = ${JSON.stringify({ params }, null, 4)}\n\nresponse = requests.post(url, headers=headers, json=body)\nprint(response.json())`,
  };
}
async function copyText(value: string) { await navigator.clipboard.writeText(value); ElMessage.success("示例已复制"); }
function downloadFile(name: string, content: string, type: string) { const url = URL.createObjectURL(new Blob([content], { type })); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url); }
function downloadMarkdown() {
  const api = docApi.value; if (!api) return;
  const parameterRows = (api.parameters || []).map((item: any) => `| ${item.name} | ${item.type} | ${item.required ? "是" : "否"} |`).join("\n") || "| - | - | - |";
  const fields = docResponseFields.value.length ? docResponseFields.value.map((field: string) => `- \`${field}\``).join("\n") : "- 由查询结果动态确定";
  const md = [`# ${api.api_name}`, "", api.description || "暂无服务说明", "", "## 基本信息", "", `- 服务编码：\`${api.service_code}\``, `- 请求方式：\`${api.method}\``, `- 请求地址：\`${externalApiUrl(api)}\``, "- 鉴权请求头：`X-API-Key: YOUR_APP_KEY`", `- 更新时间：${formatDocTime(api.updated_at)}`, "", "## 请求参数", "", "| 参数名 | 类型 | 必填 |", "| --- | --- | --- |", parameterRows, "", "## 返回字段", "", fields, "", "## curl 示例", "", "```bash", docSamples.value.curl, "```", "", "## Python 示例", "", "```python", docSamples.value.python, "```", "", "> 请将 YOUR_APP_KEY 替换为实际 AppKey，文档不包含真实凭证。", ""].join("\n");
  downloadFile(`${api.service_code}.md`, md, "text/markdown;charset=utf-8");
}
function parameterSchema(item: any) { const raw = String(item.type || "string"); if (["integer", "int"].includes(raw)) return { type: "integer" }; if (["float", "number"].includes(raw)) return { type: "number" }; if (["boolean", "bool"].includes(raw)) return { type: "boolean" }; if (["array", "list"].includes(raw)) return { type: "array", items: { type: "string" } }; if (raw === "date") return { type: "string", format: "date" }; return { type: "string" }; }
function downloadOpenApi() {
  const api = docApi.value; if (!api) return;
  const parameters = api.parameters || [];
  const operation: any = { summary: api.api_name, description: api.description || "", security: [{ AppKeyAuth: [] }], responses: { "200": { description: "调用成功", content: { "application/json": { schema: { type: "object" } } } }, "401": { description: "AppKey 无效" }, "400": { description: "请求参数错误" } } };
  if (api.method === "GET") operation.parameters = parameters.map((item: any) => ({ name: item.name, in: "query", required: !!item.required, schema: parameterSchema(item) }));
  else operation.requestBody = { required: true, content: { "application/json": { schema: { type: "object", properties: { params: { type: "object", properties: Object.fromEntries(parameters.map((item: any) => [item.name, parameterSchema(item)])), required: parameters.filter((item: any) => item.required).map((item: any) => item.name) } }, required: ["params"] } } } };
  const spec = { openapi: "3.0.3", info: { title: api.api_name, version: "1.0.0", description: api.description || "" }, servers: [{ url: window.location.origin }], paths: { [`/api/v1${api.api_path}`]: { [String(api.method).toLowerCase()]: operation } }, components: { securitySchemes: { AppKeyAuth: { type: "apiKey", in: "header", name: "X-API-Key" } } } };
  downloadFile(`${api.service_code}.openapi.json`, JSON.stringify(spec, null, 2), "application/json;charset=utf-8");
}

onMounted(async () => { await Promise.all([fetchList(), loadDatasources(), loadMetrics()]); });
</script>

<style scoped lang="scss">
.service-page { padding: 16px; }
.page-header { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.page-title { font-size:18px; font-weight:650; color:var(--el-text-color-primary); }
.page-subtitle,.secondary { margin-top:4px; color:var(--el-text-color-secondary); font-size:12px; }
.toolbar { display:flex; align-items:center; gap:10px; margin-bottom:14px; }
.service-count { margin-left:auto; color:var(--el-text-color-secondary); font-size:13px; }
.service-name { font-weight:600; }
code { margin-left:8px; color:#475569; font-family:Consolas,monospace; font-size:12px; }
.pagination { display:flex; justify-content:flex-end; margin-top:16px; }
.steps { margin:4px 10px 28px; }
.service-form { max-width:900px; margin:0 auto; }
.step-panel { min-height:480px; }
.step-panel > .el-alert { margin-bottom:22px; }
.field-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); width:100%; gap:4px 12px; padding:12px; max-height:310px; overflow:auto; border:1px solid var(--el-border-color-lighter); border-radius:6px; }
.field-grid .el-checkbox { min-width:0; margin-right:0; }
.field-grid small { margin-left:5px; color:var(--el-text-color-secondary); }
.option-meta { float:right; margin-left:30px; color:var(--el-text-color-secondary); font-size:12px; }
.param-list { width:100%; }
.param-row { display:grid; grid-template-columns:1fr 160px 80px 32px; align-items:center; gap:8px; margin-bottom:8px; }
.sql-preview { margin:0; padding:10px; max-height:180px; overflow:auto; border-radius:5px; background:#0f172a; color:#dbeafe; font-family:Consolas,monospace; white-space:pre-wrap; }
.drawer-footer { display:flex; align-items:center; justify-content:space-between; width:100%; }
.test-path { display:flex; align-items:center; gap:4px; margin-bottom:18px; padding:12px; border-radius:6px; background:var(--el-fill-color-light); }
.test-form { max-height:220px; overflow:auto; }
.result-meta { display:flex; gap:8px; margin-bottom:10px; }
.unit-text { margin-left:8px; color:var(--el-text-color-secondary); }
.key-create { display:grid; grid-template-columns:1fr auto; gap:10px; margin:16px 0; }
.created-key { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-top:8px; }
.created-key code { flex:1; padding:7px 9px; overflow:auto; border-radius:4px; background:#fff7ed; color:#9a3412; }
.key-usage { margin-top:14px; }
.api-doc { max-height:72vh; overflow:auto; padding-right:4px; }
.doc-header { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:16px; }
.doc-header h2 { margin:0; font-size:20px; }
.doc-header p { margin:6px 0 0; color:var(--el-text-color-secondary); }
.api-doc h3 { margin:22px 0 10px; font-size:15px; }
.response-fields { display:flex; flex-wrap:wrap; gap:8px; }
.code-block { position:relative; border-radius:6px; background:#0f172a; }
.code-block .el-button { position:absolute; top:8px; right:8px; }
.code-block pre { margin:0; padding:16px 74px 16px 16px; overflow:auto; color:#dbeafe; font:12px/1.7 Consolas,monospace; white-space:pre-wrap; }
.api-doc > .el-alert { margin-top:20px; }
@media(max-width:900px){.field-grid{grid-template-columns:1fr 1fr}.step-panel :deep(.el-col-12){max-width:100%;flex:0 0 100%}}
</style>
