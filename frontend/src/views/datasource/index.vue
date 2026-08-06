<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据源管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增数据源</el-button>
        </div>
      </template>

      <el-form :inline="true" class="search-form">
        <el-form-item label="类型">
          <el-select v-model="search.type" placeholder="全部" clearable style="width: 120px;" @change="loadData">
            <el-option label="MySQL" value="mysql" />
            <el-option label="Oracle" value="oracle" />
            <el-option label="PostgreSQL" value="postgresql" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" border>
        <el-table-column prop="source_name" label="名称" />
        <el-table-column prop="source_type" label="类型" width="100" />
        <el-table-column prop="host" label="地址" />
        <el-table-column prop="database_name" label="数据库" width="120" />
        <el-table-column label="连接状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.last_connection_ok ? 'success' : 'danger'" size="small">
              {{ row.last_connection_ok ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleTest(row)">测试</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑数据源' : '新增数据源'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="名称" prop="source_name">
          <el-input v-model="form.source_name" placeholder="请输入数据源名称" />
        </el-form-item>
        <el-form-item label="类型" prop="source_type">
          <el-select v-model="form.source_type" placeholder="选择类型" style="width: 100%;">
            <el-option label="MySQL" value="mysql" />
            <el-option label="Oracle" value="oracle" />
            <el-option label="PostgreSQL" value="postgresql" />
          </el-select>
        </el-form-item>
        <el-form-item label="地址" prop="host">
          <el-input v-model="form.host" placeholder="如 192.168.1.100" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" controls-position="right" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="数据库名" prop="database_name">
          <el-input v-model="form.database_name" placeholder="数据库名" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" />
        </el-form-item>
        <el-form-item label="Schema">
          <el-input v-model="form.default_schema" placeholder="默认 Schema (可选)" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="数据源描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { datasourceApi } from "@/api";

interface DataSourceForm {
  source_name: string;
  source_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  default_schema: string;
  description: string;
}

const loading = ref(false);
const tableData = ref<any[]>([]);
const search = ref({ type: "" });
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const defaultForm: DataSourceForm = {
  source_name: "",
  source_type: "mysql",
  host: "",
  port: 3306,
  database_name: "",
  username: "",
  password: "",
  default_schema: "",
  description: "",
};

const form = reactive<DataSourceForm>({ ...defaultForm });

const formRules = {
  source_name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  source_type: [{ required: true, message: "请选择类型", trigger: "change" }],
  host: [{ required: true, message: "请输入地址", trigger: "blur" }],
  port: [{ required: true, message: "请输入端口", trigger: "blur" }],
  database_name: [{ required: true, message: "请输入数据库名", trigger: "blur" }],
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await datasourceApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      source_type: search.value.type || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false;
  }
}

async function handleTest(row: any) {
  try {
    const res = await datasourceApi.testConnection(row.id);
    ElMessage.success(`连接成功 (${res.version || "OK"})`);
    loadData();
  } catch {
    // handled by interceptor
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
    source_name: row.source_name,
    source_type: row.source_type,
    host: row.host,
    port: row.port,
    database_name: row.database_name || "",
    username: row.username,
    password: "", // password is not returned from API
    default_schema: row.default_schema || "",
    description: row.description || "",
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
        const payload: Record<string, any> = { ...form };
        if (!payload.password) delete payload.password;
        await datasourceApi.update(editId.value, payload);
        ElMessage.success("更新成功");
      } else {
        await datasourceApi.create(form);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch {
      // handled by interceptor
    } finally {
      submitting.value = false;
    }
  });
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除数据源 "${row.source_name}"?`, "提示", { type: "warning" });
  await datasourceApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function resetForm() {
  formRef.value?.resetFields();
  Object.assign(form, defaultForm);
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-form {
  margin-bottom: 16px;
}
</style>
