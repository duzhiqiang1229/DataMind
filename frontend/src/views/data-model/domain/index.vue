<template>
  <div class="domain-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <div class="title">数据域划分</div>
            <div class="subtitle">按稳定的业务责任边界组织数仓资产</div>
          </div>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建数据域</el-button>
        </div>
      </template>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column prop="sort_order" label="顺序" width="72" align="center" />
        <el-table-column prop="domain_name" label="数据域" min-width="150">
          <template #default="{ row }">
            <div class="domain-name">{{ row.domain_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="domain_code" label="编码" width="180">
          <template #default="{ row }"><code>{{ row.domain_code }}</code></template>
        </el-table-column>
        <el-table-column prop="description" label="范围说明" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="尚未划分数据域" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑数据域' : '新建数据域'" width="540px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="88px">
        <el-form-item label="数据域" prop="domain_name">
          <el-input v-model="form.domain_name" placeholder="例如：收费财务域" />
        </el-form-item>
        <el-form-item label="编码" prop="domain_code">
          <el-input v-model="form.domain_code" placeholder="例如：fee_finance" :disabled="Boolean(editId)" />
        </el-form-item>
        <el-form-item label="范围说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="说明纳入和不纳入的数据范围" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :step="10" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataModelApi } from "@/api";

const loading = ref(false);
const saving = ref(false);
const items = ref<any[]>([]);
const dialogVisible = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();
const form = reactive({ domain_name: "", domain_code: "", description: "", sort_order: 10 });
const formRules = {
  domain_name: [{ required: true, message: "请输入数据域名称", trigger: "blur" }],
  domain_code: [{ required: true, message: "请输入稳定的英文编码", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    items.value = (await dataModelApi.dataDomains()) || [];
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  Object.assign(form, { domain_name: "", domain_code: "", description: "", sort_order: (items.value.length + 1) * 10 });
  formRef.value?.clearValidate();
}

function openCreate() {
  editId.value = "";
  resetForm();
  dialogVisible.value = true;
}

function openEdit(row: any) {
  editId.value = row.id;
  Object.assign(form, row);
  dialogVisible.value = true;
}

async function handleSave() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    if (editId.value) await dataModelApi.updateDataDomain(editId.value, { ...form });
    else await dataModelApi.createDataDomain({ ...form });
    ElMessage.success("数据域已保存");
    dialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除数据域“${row.domain_name}”？请先确认没有业务过程和模型继续使用。`, "删除确认", { type: "warning" });
  await dataModelApi.deleteDataDomain(row.id);
  ElMessage.success("数据域已删除");
  await loadData();
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.domain-page { display: flex; flex-direction: column; gap: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 16px; font-weight: 600; }
.subtitle { margin-top: 4px; font-size: 13px; color: var(--el-text-color-secondary); }
.domain-name { font-weight: 600; }
code { color: var(--el-color-primary); background: var(--el-fill-color-light); padding: 2px 6px; border-radius: 4px; }
</style>
