<template>
  <div class="data-service-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据服务</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增 API</el-button>
        </div>
      </template>

      <el-table :data="tableData" border v-loading="loading">
        <el-table-column prop="api_name" label="API 名称" min-width="140" />
        <el-table-column prop="api_path" label="路径" min-width="180">
          <template #default="{ row }">
            <el-tag :type="methodTagType(row.method)" size="small" style="margin-right: 6px;">
              {{ row.method }}
            </el-tag>
            <span>{{ row.api_path }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip min-width="200" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === "active" ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="call_count" label="调用次数" width="100" />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }: { row: any }">
            <el-button link type="success" @click="handleTest(row)">测试</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 API' : '新增 API'"
      width="900px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="API 名称" prop="api_name">
              <el-input v-model="form.api_name" placeholder="如 get_user_orders" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="请求方法" prop="method">
              <el-select v-model="form.method" style="width: 100%;">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="路径" prop="api_path">
              <el-input v-model="form.api_path" placeholder="如 /api/orders/users/{user_id}" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="API 功能描述" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库">
              <el-input v-model="form.database" placeholder="如 analytics_db" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="SQL 模板" prop="sql_template">
              <el-input
                v-model="form.sql_template"
                type="textarea"
                :rows="5"
                placeholder="SELECT * FROM orders WHERE user_id = {{user_id}} LIMIT {{limit}}"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="参数列表">
              <div class="param-list">
                <div v-for="(param, index) in form.parameters" :key="index" class="param-row">
                  <el-input v-model="param.name" placeholder="参数名" style="width: 160px;" />
                  <el-select v-model="param.type" placeholder="类型" style="width: 130px;">
                    <el-option label="string" value="string" />
                    <el-option label="integer" value="integer" />
                    <el-option label="boolean" value="boolean" />
                    <el-option label="float" value="float" />
                    <el-option label="date" value="date" />
                  </el-select>
                  <el-checkbox v-model="param.required">必填</el-checkbox>
                  <el-button link type="danger" :icon="Delete" @click="removeParam(index)" />
                </div>
                <el-button link type="primary" :icon="Plus" @click="addParam">添加参数</el-button>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
    <el-dialog v-model="testDialogVisible" title="API 测试" width="800px" @close="onTestClose">
      <div v-if="currentTestApi">
        <el-descriptions :column="1" border size="small" style="margin-bottom: 16px;">
          <el-descriptions-item label="API">{{ currentTestApi.api_name }}</el-descriptions-item>
          <el-descriptions-item label="路径">
            <el-tag :type="methodTagType(currentTestApi.method)" size="small" style="margin-right: 6px;">
              {{ currentTestApi.method }}
            </el-tag>
            {{ currentTestApi.api_path }}
          </el-descriptions-item>
          <el-descriptions-item v-if="currentTestApi.database" label="数据库">
            {{ currentTestApi.database }}
          </el-descriptions-item>
        </el-descriptions>

        <el-form label-width="120px" v-if="testParams.length > 0">
          <el-form-item
            v-for="param in testParams"
            :key="param.name"
            :label="param.name"
          >
            <el-input
              v-model="param.value"
              :placeholder="`类型: ${param.type}${param.required ? ' (必填)' : ''}`"
            />
          </el-form-item>
        </el-form>
        <el-empty v-else description="该 API 无参数" :image-size="40" />

        <el-divider />

        <div class="test-response">
          <div class="response-header">
            <span>响应结果</span>
            <span v-if="testResult" class="response-meta">
              <el-tag size="small" type="info">{{ testResult.row_count }} 行</el-tag>
              <el-tag size="small" type="success" style="margin-left: 6px;">{{ testResult.elapsed_ms }} ms</el-tag>
              <el-tag v-if="testResult.truncated" size="small" type="warning" style="margin-left: 6px;">已截断</el-tag>
            </span>
          </div>

          <el-table
            v-if="testResult && testResult.rows.length > 0"
            :data="testResult.rows"
            border
            max-height="400"
            style="margin-top: 8px;"
          >
            <el-table-column
              v-for="col in testResult.columns"
              :key="col"
              :prop="col"
              :label="col"
              min-width="120"
              show-overflow-tooltip
            />
          </el-table>

          <el-empty
            v-else-if="testResult"
            description="查询结果为空"
            :image-size="40"
          />
          <el-empty
            v-else
            description="点击「执行」查看结果"
            :image-size="40"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="testing" @click="handleExecuteTest">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataServiceApi } from "@/api";
import { formatDateTime } from "@/utils/format";

interface ApiParameter {
  name: string;
  type: string;
  required: boolean;
}

interface DataServiceApi {
  id: string;
  api_name: string;
  api_path: string;
  method: "GET" | "POST";
  status: string;
  description: string;
  sql_template: string;
  parameters: ApiParameter[];
  database: string;
  call_count: number;
  created_at: string;
}

interface TestParam {
  name: string;
  type: string;
  required: boolean;
  value: string;
}

interface ExecuteResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  truncated: boolean;
  elapsed_ms: number;
}

type TagType = "primary" | "success" | "warning" | "info" | "danger";

// ---------- Table & pagination ----------
const tableData = ref<DataServiceApi[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

async function fetchList() {
  loading.value = true;
  try {
    const res = await dataServiceApi.list({
      page: page.value,
      page_size: pageSize.value,
    }) as { items: DataServiceApi[]; total: number };
    tableData.value = res.items || [];
    total.value = res.total || 0;
  } catch {
    // error already handled by interceptor
  } finally {
    loading.value = false;
  }
}

function methodTagType(method: string): TagType {
  return method === "GET" ? "success" : "primary";
}

// ---------- Create/Edit dialog ----------
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

interface FormState {
  api_name: string;
  api_path: string;
  method: "GET" | "POST";
  description: string;
  sql_template: string;
  database: string;
  parameters: ApiParameter[];
}

const form = reactive<FormState>({
  api_name: "",
  api_path: "",
  method: "GET",
  description: "",
  sql_template: "",
  database: "",
  parameters: [],
});

const formRules = {
  api_name: [{ required: true, message: "请输入 API 名称", trigger: "blur" }],
  api_path: [{ required: true, message: "请输入路径", trigger: "blur" }],
  method: [{ required: true, message: "请选择请求方法", trigger: "change" }],
  sql_template: [{ required: true, message: "请输入 SQL 模板", trigger: "blur" }],
};

function resetFormState() {
  form.api_name = "";
  form.api_path = "";
  form.method = "GET";
  form.description = "";
  form.sql_template = "";
  form.database = "";
  form.parameters = [];
}

function handleAdd() {
  isEdit.value = false;
  resetFormState();
  dialogVisible.value = true;
}

async function handleEdit(row: DataServiceApi) {
  isEdit.value = true;
  editId.value = row.id;
  try {
    const detail = await dataServiceApi.detail(row.id) as DataServiceApi;
    form.api_name = detail.api_name || "";
    form.api_path = detail.api_path || "";
    form.method = detail.method || "GET";
    form.description = detail.description || "";
    form.sql_template = detail.sql_template || "";
    form.database = detail.database || "";
    form.parameters = (detail.parameters || []).map((p) => ({ ...p }));
    dialogVisible.value = true;
  } catch {
    // error handled by interceptor
  }
}

function addParam() {
  form.parameters.push({ name: "", type: "string", required: false });
}

function removeParam(index: number) {
  form.parameters.splice(index, 1);
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      const validParams = form.parameters.filter((p) => p.name.trim());
      const payload = {
        api_name: form.api_name,
        api_path: form.api_path,
        method: form.method,
        description: form.description,
        sql_template: form.sql_template,
        database: form.database,
        parameters: validParams,
      };
      if (isEdit.value) {
        await dataServiceApi.update(editId.value, payload);
        ElMessage.success("更新成功");
      } else {
        await dataServiceApi.create(payload);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      fetchList();
    } catch {
      // error handled by interceptor
    } finally {
      submitting.value = false;
    }
  });
}

async function handleDelete(row: DataServiceApi) {
  try {
    await ElMessageBox.confirm(`确认删除 API "${row.api_name}"?`, "提示", { type: "warning" });
    await dataServiceApi.delete(row.id);
    ElMessage.success("删除成功");
    fetchList();
  } catch {
    // user cancelled or error handled by interceptor
  }
}

// ---------- Test dialog ----------
const testDialogVisible = ref(false);
const currentTestApi = ref<DataServiceApi | null>(null);
const testParams = ref<TestParam[]>([]);
const testResult = ref<ExecuteResult | null>(null);
const testing = ref(false);

function handleTest(row: DataServiceApi) {
  currentTestApi.value = row;
  testParams.value = (row.parameters || []).map((p) => ({
    name: p.name,
    type: p.type,
    required: p.required,
    value: "",
  }));
  testResult.value = null;
  testDialogVisible.value = true;
}

function onTestClose() {
  currentTestApi.value = null;
  testParams.value = [];
  testResult.value = null;
}

async function handleExecuteTest() {
  if (!currentTestApi.value) return;

  const missing = testParams.value.filter((p) => p.required && !p.value.trim());
  if (missing.length > 0) {
    ElMessage.warning(`必填参数缺失: ${missing.map((p) => p.name).join(", ")}`);
    return;
  }

  testing.value = true;
  testResult.value = null;
  try {
    const params: Record<string, any> = {};
    testParams.value.forEach((p) => {
      if (p.value.trim()) {
        params[p.name] = p.value;
      }
    });

    const result = await dataServiceApi.execute(currentTestApi.value.id, params) as ExecuteResult;
    testResult.value = {
      columns: result.columns || [],
      rows: result.rows || [],
      row_count: result.row_count ?? 0,
      truncated: result.truncated ?? false,
      elapsed_ms: result.elapsed_ms ?? 0,
    };
    ElMessage.success("执行完成");
  } catch {
    // error handled by interceptor
  } finally {
    testing.value = false;
  }
}

function resetForm() {
  formRef.value?.resetFields();
  resetFormState();
}

// ---------- Init ----------
onMounted(() => {
  fetchList();
});
</script>

<style lang="scss" scoped>
.data-service-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }

  .param-list {
    width: 100%;

    .param-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
  }

  .test-response {
    .response-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-weight: 600;
      color: #303133;
    }

    .response-meta {
      font-weight: normal;
    }
  }
}
</style>
