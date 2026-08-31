<template>
  <div class="process-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <div class="title">业务过程</div>
            <div class="subtitle">从数据域继续拆分到可度量、可建模的业务活动</div>
          </div>
          <div class="actions">
            <el-select v-model="domainFilter" clearable placeholder="全部数据域" style="width: 170px">
              <el-option v-for="domain in domains" :key="domain.domain_code" :label="domain.domain_name" :value="domain.domain_name" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="openCreate">新建业务过程</el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredItems" v-loading="loading" border stripe>
        <el-table-column prop="sort_order" label="顺序" width="72" align="center" />
        <el-table-column prop="domain_name" label="业务过程" min-width="170">
          <template #default="{ row }"><strong>{{ row.domain_name }}</strong></template>
        </el-table-column>
        <el-table-column prop="domain_code" label="编码" width="190">
          <template #default="{ row }"><code>{{ row.domain_code }}</code></template>
        </el-table-column>
        <el-table-column label="所属数据域" width="150">
          <template #default="{ row }"><el-tag effect="plain">{{ row.data_domain || "未归属" }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="description" label="过程说明" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="尚未定义业务过程" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑业务过程' : '新建业务过程'" width="560px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-form-item label="业务过程" prop="domain_name">
          <el-input v-model="form.domain_name" placeholder="例如：费用实收" />
        </el-form-item>
        <el-form-item label="过程编码" prop="domain_code">
          <el-input v-model="form.domain_code" placeholder="例如：fee_collection" :disabled="Boolean(editId)" />
        </el-form-item>
        <el-form-item label="所属数据域" prop="data_domain">
          <el-select v-model="form.data_domain" filterable placeholder="选择数据域" style="width: 100%">
            <el-option v-for="domain in domains" :key="domain.domain_code" :label="domain.domain_name" :value="domain.domain_name" />
          </el-select>
        </el-form-item>
        <el-form-item label="过程说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="说明业务何时发生、产生什么事实" />
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
import { computed, onMounted, reactive, ref } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataModelApi } from "@/api";

const loading = ref(false);
const saving = ref(false);
const items = ref<any[]>([]);
const domains = ref<any[]>([]);
const domainFilter = ref("");
const dialogVisible = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();
const form = reactive({ domain_name: "", domain_code: "", data_domain: "", description: "", sort_order: 10 });
const formRules = {
  domain_name: [{ required: true, message: "请输入业务过程名称", trigger: "blur" }],
  domain_code: [{ required: true, message: "请输入稳定的英文编码", trigger: "blur" }],
  data_domain: [{ required: true, message: "请选择所属数据域", trigger: "change" }],
};
const filteredItems = computed(() => domainFilter.value ? items.value.filter(item => item.data_domain === domainFilter.value) : items.value);

async function loadData() {
  loading.value = true;
  try {
    const [processes, domainRows] = await Promise.all([dataModelApi.businessDomains(), dataModelApi.dataDomains()]);
    items.value = processes || [];
    domains.value = domainRows || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editId.value = "";
  Object.assign(form, { domain_name: "", domain_code: "", data_domain: domainFilter.value, description: "", sort_order: (items.value.length + 1) * 10 });
  formRef.value?.clearValidate();
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
    if (editId.value) await dataModelApi.updateBusinessDomain(editId.value, { ...form });
    else await dataModelApi.createBusinessDomain({ ...form });
    ElMessage.success("业务过程已保存");
    dialogVisible.value = false;
    await loadData();
  } finally {
    saving.value = false;
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除业务过程“${row.domain_name}”？请先确认没有模型继续使用。`, "删除确认", { type: "warning" });
  await dataModelApi.deleteBusinessDomain(row.id);
  ElMessage.success("业务过程已删除");
  await loadData();
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.process-page { display: flex; flex-direction: column; gap: 16px; }
.card-header, .actions { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.title { font-size: 16px; font-weight: 600; }
.subtitle { margin-top: 4px; font-size: 13px; color: var(--el-text-color-secondary); }
code { color: var(--el-color-primary); background: var(--el-fill-color-light); padding: 2px 6px; border-radius: 4px; }
</style>
