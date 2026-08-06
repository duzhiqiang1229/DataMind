<template>
  <div class="data-service-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据服务</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增 API</el-button>
        </div>
      </template>

      <el-alert
        type="warning"
        :closable="false"
        style="margin-bottom: 16px;"
      >
        数据服务功能正在开发中，当前为演示模式
      </el-alert>

      <el-table :data="tableData" border>
        <el-table-column prop="api_name" label="API 名称" min-width="140" />
        <el-table-column prop="api_path" label="路径" min-width="180">
          <template #default="{ row }">
            <el-tag :type="row.method === 'GET' ? 'success' : 'primary'" size="small" style="margin-right: 6px;">
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
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }: { row: any }">
            <el-button text type="primary" @click="handleTest(row)">测试</el-button>
            <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="tableData.length === 0" description="暂无数据服务 API，点击「新增 API」创建" />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 API' : '新增 API'"
      width="700px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="API 名称" prop="api_name">
          <el-input v-model="form.api_name" placeholder="如 get_user_orders" />
        </el-form-item>
        <el-form-item label="路径" prop="api_path">
          <el-input v-model="form.api_path" placeholder="如 /api/orders/users/{user_id}" />
        </el-form-item>
        <el-form-item label="请求方法" prop="method">
          <el-select v-model="form.method" style="width: 200px;">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="API 功能描述" />
        </el-form-item>
        <el-form-item label="SQL 模板" prop="sql_template">
          <el-input
            v-model="form.sql_template"
            type="textarea"
            :rows="5"
            placeholder="SELECT * FROM orders WHERE user_id = {{user_id}} LIMIT {{limit}}"
          />
        </el-form-item>

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
              <el-button text type="danger" :icon="Delete" @click="removeParam(index)" />
            </div>
            <el-button text type="primary" :icon="Plus" @click="addParam">添加参数</el-button>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
    <el-dialog v-model="testDialogVisible" title="API 测试" width="700px">
      <div v-if="currentTestApi">
        <el-descriptions :column="1" border size="small" style="margin-bottom: 16px;">
          <el-descriptions-item label="API">{{ currentTestApi.api_name }}</el-descriptions-item>
          <el-descriptions-item label="路径">
            <el-tag :type="currentTestApi.method === 'GET' ? 'success' : 'primary'" size="small">
              {{ currentTestApi.method }}
            </el-tag>
            {{ currentTestApi.api_path }}
          </el-descriptions-item>
        </el-descriptions>

        <el-form label-width="100px" v-if="testParams.length > 0">
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
            <el-button
              v-if="testResult"
              text
              type="primary"
              size="small"
              @click="testResult = null"
            >
              清除
            </el-button>
          </div>
          <pre v-if="testResult" class="response-body">{{ testResult }}</pre>
          <el-empty v-else description="点击「执行」查看结果" :image-size="40" />
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
import { ref, reactive } from "vue";
import { Plus, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";

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
  status: "active" | "inactive";
  description: string;
  sql_template: string;
  parameters: ApiParameter[];
}

interface TestParam {
  name: string;
  type: string;
  required: boolean;
  value: string;
}

const tableData = ref<DataServiceApi[]>([
  {
    id: "1",
    api_name: "get_user_orders",
    api_path: "/api/orders/users/{user_id}",
    method: "GET",
    status: "active",
    description: "查询指定用户的订单列表",
    sql_template: "SELECT * FROM orders WHERE user_id = {{user_id}} LIMIT {{limit}}",
    parameters: [
      { name: "user_id", type: "integer", required: true },
      { name: "limit", type: "integer", required: false },
    ],
  },
  {
    id: "2",
    api_name: "get_product_detail",
    api_path: "/api/products/{product_id}",
    method: "GET",
    status: "active",
    description: "获取商品详情信息",
    sql_template: "SELECT * FROM products WHERE id = {{product_id}}",
    parameters: [
      { name: "product_id", type: "integer", required: true },
    ],
  },
  {
    id: "3",
    api_name: "create_order",
    api_path: "/api/orders",
    method: "POST",
    status: "inactive",
    description: "创建新订单",
    sql_template: "INSERT INTO orders (user_id, product_id, quantity) VALUES ({{user_id}}, {{product_id}}, {{quantity}})",
    parameters: [
      { name: "user_id", type: "integer", required: true },
      { name: "product_id", type: "integer", required: true },
      { name: "quantity", type: "integer", required: false },
    ],
  },
]);

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const defaultForm = {
  api_name: "",
  api_path: "",
  method: "GET" as "GET" | "POST",
  description: "",
  sql_template: "",
  parameters: [] as ApiParameter[],
};

const form = reactive<{ api_name: string; api_path: string; method: "GET" | "POST"; description: string; sql_template: string; parameters: ApiParameter[] }>({ ...defaultForm, parameters: [] });

const formRules = {
  api_name: [{ required: true, message: "请输入 API 名称", trigger: "blur" }],
  api_path: [{ required: true, message: "请输入路径", trigger: "blur" }],
  method: [{ required: true, message: "请选择请求方法", trigger: "change" }],
  sql_template: [{ required: true, message: "请输入 SQL 模板", trigger: "blur" }],
};

const testDialogVisible = ref(false);
const currentTestApi = ref<DataServiceApi | null>(null);
const testParams = ref<TestParam[]>([]);
const testResult = ref<string | null>(null);
const testing = ref(false);

let idCounter = 4;

function handleAdd() {
  isEdit.value = false;
  Object.assign(form, defaultForm, { parameters: [] });
  form.parameters = [];
  dialogVisible.value = true;
}

function handleEdit(row: DataServiceApi) {
  isEdit.value = true;
  editId.value = row.id;
  Object.assign(form, {
    api_name: row.api_name,
    api_path: row.api_path,
    method: row.method,
    description: row.description || "",
    sql_template: row.sql_template || "",
    status: row.status,
    parameters: [],
  });
  form.parameters = row.parameters.map((p) => ({ ...p }));
  dialogVisible.value = true;
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
      if (isEdit.value) {
        const idx = tableData.value.findIndex((r) => r.id === editId.value);
        if (idx > -1) {
          tableData.value[idx] = {
            ...tableData.value[idx],
            api_name: form.api_name,
            api_path: form.api_path,
            method: form.method,
            description: form.description,
            sql_template: form.sql_template,
            parameters: validParams,
          };
        }
        ElMessage.success("更新成功");
      } else {
        tableData.value.push({
          id: String(idCounter++),
          api_name: form.api_name,
          api_path: form.api_path,
          method: form.method,
          status: "active",
          description: form.description,
          sql_template: form.sql_template,
          parameters: validParams,
        });
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
    } catch {
      /* handled */
    } finally {
      submitting.value = false;
    }
  });
}

async function handleDelete(row: DataServiceApi) {
  await ElMessageBox.confirm(`确认删除 API "${row.api_name}"?`, "提示", { type: "warning" });
  const idx = tableData.value.findIndex((r) => r.id === row.id);
  if (idx > -1) {
    tableData.value.splice(idx, 1);
    ElMessage.success("删除成功");
  }
}

function handleTest(row: DataServiceApi) {
  currentTestApi.value = row;
  testParams.value = row.parameters.map((p) => ({
    name: p.name,
    type: p.type,
    required: p.required,
    value: "",
  }));
  testResult.value = null;
  testDialogVisible.value = true;
}

async function handleExecuteTest() {
  if (!currentTestApi.value) return;

  // Validate required params
  const missing = testParams.value.filter((p) => p.required && !p.value.trim());
  if (missing.length > 0) {
    ElMessage.warning(`必填参数缺失: ${missing.map((p) => p.name).join(", ")}`);
    return;
  }

  testing.value = true;
  try {
    // Simulate API execution (backend not yet connected)
    await new Promise((resolve) => setTimeout(resolve, 600));

    const params: Record<string, string> = {};
    testParams.value.forEach((p) => {
      if (p.value.trim()) params[p.name] = p.value;
    });

    const mockResponse = {
      code: 0,
      message: "success",
      data: {
        api: currentTestApi.value.api_name,
        method: currentTestApi.value.method,
        path: currentTestApi.value.api_path,
        parameters: params,
        rows: [
          { id: 1, name: "示例数据 1", created_at: "2025-01-15 10:30:00" },
          { id: 2, name: "示例数据 2", created_at: "2025-01-15 11:00:00" },
        ],
        total: 2,
      },
      note: "演示模式：后端接口尚未对接，返回模拟数据",
    };

    testResult.value = JSON.stringify(mockResponse, null, 2);
    ElMessage.success("执行完成（模拟数据）");
  } catch {
    /* handled */
  } finally {
    testing.value = false;
  }
}

function resetForm() {
  formRef.value?.resetFields();
  Object.assign(form, defaultForm);
  form.parameters = [];
}
</script>

<style lang="scss" scoped>
.data-service-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

    .response-body {
      max-height: 300px;
      overflow-y: auto;
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 12px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-all;
      margin: 0;
    }
  }
}
</style>
