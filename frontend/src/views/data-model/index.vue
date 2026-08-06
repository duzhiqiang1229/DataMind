<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据模型管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新建模型</el-button>
        </div>
      </template>

      <el-form :inline="true" class="search-form">
        <el-form-item label="分层">
          <el-select v-model="searchLayer" placeholder="全部" clearable style="width: 120px;" @change="loadData">
            <el-option label="ODS" value="ods" />
            <el-option label="DWD" value="dwd" />
            <el-option label="DWS" value="dws" />
            <el-option label="ADS" value="ads" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" border>
        <el-table-column prop="model_name" label="模型名称" />
        <el-table-column prop="model_code" label="编码" width="150" />
        <el-table-column prop="layer" label="分层" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="layerTag(row.layer)">{{ row.layer.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="database" label="数据库" width="100" />
        <el-table-column prop="table_name" label="表名" width="150" />
        <el-table-column prop="current_version" label="版本" width="80" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="primary" @click="handleVersions(row)">版本</el-button>
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑模型' : '新建模型'" width="800px" @close="clearForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="模型名称" prop="model_name">
              <el-input v-model="form.model_name" placeholder="模型名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型编码" prop="model_code">
              <el-input v-model="form.model_code" placeholder="唯一编码" :disabled="isEdit" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="分层" prop="layer">
              <el-select v-model="form.layer" style="width: 100%;">
                <el-option label="ODS" value="ods" />
                <el-option label="DWD" value="dwd" />
                <el-option label="DWS" value="dws" />
                <el-option label="ADS" value="ads" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数据库" prop="database">
              <el-input v-model="form.database" placeholder="如 ods" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="表名" prop="table_name">
              <el-input v-model="form.table_name" placeholder="如 ods_user" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="模型描述" />
        </el-form-item>

        <el-divider content-position="left">字段定义</el-divider>
        <el-button type="primary" size="small" @click="addField" style="margin-bottom: 12px;">添加字段</el-button>
        <el-table :data="form.fields" border size="small">
          <el-table-column label="字段名" width="150">
            <template #default="{ row }">
              <el-input v-model="row.field_name" size="small" placeholder="field_name" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-input v-model="row.field_type" size="small" placeholder="VARCHAR(255)" />
            </template>
          </el-table-column>
          <el-table-column label="注释" min-width="150">
            <template #default="{ row }">
              <el-input v-model="row.field_comment" size="small" placeholder="注释" />
            </template>
          </el-table-column>
          <el-table-column label="主键" width="60">
            <template #default="{ row }">
              <el-checkbox v-model="row.is_primary_key" />
            </template>
          </el-table-column>
          <el-table-column label="分区" width="60">
            <template #default="{ row }">
              <el-checkbox v-model="row.is_partition" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ $index }">
              <el-button text type="danger" size="small" @click="form.fields.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 版本历史对话框 -->
    <el-dialog v-model="versionDialogVisible" title="版本历史" width="600px">
      <el-timeline>
        <el-timeline-item
          v-for="v in versions"
          :key="v.id"
          :timestamp="v.created_at"
          placement="top"
        >
          <el-card shadow="never">
            <h4>版本 {{ v.version }}</h4>
            <p>{{ v.change_log }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataModelApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const loading = ref(false);
const tableData = ref<any[]>([]);
const searchLayer = ref("");
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const versionDialogVisible = ref(false);
const versions = ref<any[]>([]);

const defaultForm = {
  model_name: "",
  model_code: "",
  layer: "ods",
  database: "ods",
  table_name: "",
  description: "",
  fields: [] as any[],
};

const form = reactive(JSON.parse(JSON.stringify(defaultForm)));

const formRules = {
  model_name: [{ required: true, message: "请输入模型名称", trigger: "blur" }],
  model_code: [{ required: true, message: "请输入模型编码", trigger: "blur" }],
  layer: [{ required: true, message: "请选择分层", trigger: "change" }],
  database: [{ required: true, message: "请输入数据库", trigger: "blur" }],
  table_name: [{ required: true, message: "请输入表名", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await dataModelApi.list({
      page: pagination.page, page_size: pagination.page_size,
      layer: searchLayer.value || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

function handleAdd() {
  isEdit.value = false;
  Object.assign(form, JSON.parse(JSON.stringify(defaultForm)));
  dialogVisible.value = true;
}

function handleEdit(row: any) {
  isEdit.value = true;
  editId.value = row.id;
  Object.assign(form, {
    model_name: row.model_name,
    model_code: row.model_code,
    layer: row.layer,
    database: row.database,
    table_name: row.table_name,
    description: row.description || "",
    fields: (row.fields || []).map((f: any) => ({ ...f })),
  });
  dialogVisible.value = true;
}

function addField() {
  form.fields.push({
    field_name: "", field_type: "", field_comment: "",
    is_primary_key: false, is_partition: false, sort_order: form.fields.length,
  });
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      if (isEdit.value) {
        await dataModelApi.update(editId.value, form);
        ElMessage.success("更新成功");
      } else {
        await dataModelApi.create(form);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch { /* handled */ } finally {
      submitting.value = false;
    }
  });
}

async function handleVersions(row: any) {
  try {
    const res = await dataModelApi.versions(row.id);
    versions.value = res || [];
    versionDialogVisible.value = true;
  } catch { /* handled */ }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除模型 "${row.model_name}"?`, "提示", { type: "warning" });
  await dataModelApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function clearForm() {
  formRef.value?.resetFields();
  Object.assign(form, JSON.parse(JSON.stringify(defaultForm)));
}

function layerTag(layer: string): TagType {
  const map: Record<string, TagType> = { ods: "info", dwd: "success", dws: "warning", ads: "danger" };
  return map[layer] || "info";
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.search-form { margin-bottom: 16px; }
</style>
