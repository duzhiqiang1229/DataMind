<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>组件配置</span>
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增组件</el-button>
      </div>
    </template>

    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="component_name" label="名称" />
      <el-table-column prop="component_code" label="标识" width="120" />
      <el-table-column prop="component_type" label="类型" width="120" />
      <el-table-column prop="base_url" label="地址" show-overflow-tooltip />
      <el-table-column label="健康状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.last_check_ok ? 'success' : 'danger'" size="small">
            {{ row.last_check_ok ? '正常' : '异常' }}
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
          <el-button text type="primary" @click="handleHealthCheck(row)">健康检查</el-button>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑组件' : '新增组件'" width="600px" @close="clearForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="组件标识" prop="component_code">
          <el-input v-model="form.component_code" placeholder="如 airflow/doris/cube" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="组件名称" prop="component_name">
          <el-input v-model="form.component_name" placeholder="组件名称" />
        </el-form-item>
        <el-form-item label="组件类型" prop="component_type">
          <el-select v-model="form.component_type" style="width: 100%;">
            <el-option label="调度器" value="scheduler" />
            <el-option label="OLAP" value="olap" />
            <el-option label="语义层" value="semantic" />
            <el-option label="数据治理" value="governance" />
          </el-select>
        </el-form-item>
        <el-form-item label="API地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="http://airflow:8080/api/v1" />
        </el-form-item>
        <el-form-item label="认证类型">
          <el-select v-model="form.auth_type" style="width: 100%;">
            <el-option label="无认证" value="none" />
            <el-option label="Token" value="token" />
            <el-option label="Basic Auth" value="basic" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置JSON">
          <el-input v-model="configJsonText" type="textarea" :rows="4" placeholder='{"key": "value"}' />
        </el-form-item>
        <el-form-item v-if="form.auth_type !== 'none'" label="凭据">
          <el-input v-model="credentialsText" type="textarea" :rows="2" placeholder='{"username": "...", "password": "..."}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { componentApi } from "@/api";

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();
const configJsonText = ref("{}");
const credentialsText = ref("");

const defaultForm = {
  component_code: "",
  component_name: "",
  component_type: "scheduler",
  base_url: "",
  auth_type: "none",
  config_json: {},
};

const form = reactive({ ...defaultForm });

const formRules = {
  component_code: [{ required: true, message: "请输入组件标识", trigger: "blur" }],
  component_name: [{ required: true, message: "请输入组件名称", trigger: "blur" }],
  component_type: [{ required: true, message: "请选择类型", trigger: "change" }],
  base_url: [{ required: true, message: "请输入API地址", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await componentApi.list({ page: pagination.page, page_size: pagination.page_size });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

function handleAdd() {
  isEdit.value = false;
  Object.assign(form, defaultForm);
  configJsonText.value = "{}";
  credentialsText.value = "";
  dialogVisible.value = true;
}

function handleEdit(row: any) {
  isEdit.value = true;
  editId.value = row.id;
  Object.assign(form, {
    component_code: row.component_code,
    component_name: row.component_name,
    component_type: row.component_type,
    base_url: row.base_url,
    auth_type: row.auth_type || "none",
    config_json: row.config_json || {},
  });
  configJsonText.value = JSON.stringify(row.config_json || {}, null, 2);
  credentialsText.value = "";
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      let configJson: any = {};
      try { configJson = JSON.parse(configJsonText.value || "{}"); }
      catch { ElMessage.error("配置JSON格式错误"); submitting.value = false; return; }

      const payload: any = { ...form, config_json: configJson };
      if (credentialsText.value) {
        try { payload.credentials = JSON.parse(credentialsText.value); }
        catch { ElMessage.error("凭据JSON格式错误"); submitting.value = false; return; }
      }

      if (isEdit.value) {
        await componentApi.update(editId.value, payload);
        ElMessage.success("更新成功");
      } else {
        await componentApi.create(payload);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch { /* handled */ } finally {
      submitting.value = false;
    }
  });
}

async function handleHealthCheck(row: any) {
  try {
    const res = await componentApi.healthCheck(row.component_code);
    ElMessage[res.healthy ? "success" : "error"](`${row.component_name}: ${res.message || (res.healthy ? "正常" : "异常")}`);
    loadData();
  } catch { /* handled */ }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除组件 "${row.component_name}"?`, "提示", { type: "warning" });
  await componentApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function clearForm() {
  formRef.value?.resetFields();
  Object.assign(form, defaultForm);
  configJsonText.value = "{}";
  credentialsText.value = "";
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
