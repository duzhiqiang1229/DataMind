<template>
  <el-card shadow="never" class="page-card">
    <template #header>
      <div class="card-header">
        <span>业务过程</span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建业务过程</el-button>
      </div>
    </template>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="domain_name" label="业务过程名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="domain_code" label="编码" width="160" show-overflow-tooltip />
      <el-table-column label="所属数据域" width="140">
        <template #default="{ row }">
          <el-tag v-if="row.data_domain" size="small" effect="plain">{{ row.data_domain }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '-' }}</template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="80" align="center" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑业务过程' : '新建业务过程'" width="520px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
        <el-form-item label="业务过程" prop="domain_name">
          <el-input v-model="form.domain_name" placeholder="如：订单支付" />
        </el-form-item>
        <el-form-item label="编码" prop="domain_code">
          <el-input v-model="form.domain_code" placeholder="如 order_pay，留空自动取名称" />
        </el-form-item>
        <el-form-item label="所属数据域">
          <el-select v-model="form.data_domain" clearable filterable placeholder="选择数据域" style="width: 100%;">
            <el-option v-for="d in domainOptions" :key="d.domain_name" :label="d.domain_name" :value="d.domain_name" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="业务过程描述" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { dataModelApi } from "@/api";

const loading = ref(false);
const items = ref<any[]>([]);
const dialogVisible = ref(false);
const saving = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();
const domainOptions = ref<any[]>([]);

const form = reactive({ domain_name: "", domain_code: "", data_domain: "", description: "", sort_order: 0 });
const formRules = {
  domain_name: [{ required: true, message: "请输入业务过程名称", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await dataModelApi.businessDomains();
    items.value = res || [];
  } catch {
    // handled
  } finally {
    loading.value = false;
  }
}

async function loadDomains() {
  try {
    const res = await dataModelApi.dataDomains();
    domainOptions.value = res || [];
  } catch {
    // handled
  }
}

function openCreate() {
  editId.value = "";
  Object.assign(form, { domain_name: "", domain_code: "", data_domain: "", description: "", sort_order: 0 });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  editId.value = row.id;
  Object.assign(form, {
    domain_name: row.domain_name || "",
    domain_code: row.domain_code || "",
    data_domain: row.data_domain || "",
    description: row.description || "",
    sort_order: row.sort_order || 0,
  });
  dialogVisible.value = true;
}

async function handleSave() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    saving.value = true;
    try {
      const payload = { ...form };
      if (editId.value) {
        await dataModelApi.updateBusinessDomain(editId.value, payload);
        ElMessage.success("更新成功");
      } else {
        await dataModelApi.createBusinessDomain(payload);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch {
      // handled
    } finally {
      saving.value = false;
    }
  });
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除业务过程 "${row.domain_name}"？`, "删除确认", { type: "warning" });
  try {
    await dataModelApi.deleteBusinessDomain(row.id);
    ElMessage.success("删除成功");
    loadData();
  } catch {
    // handled
  }
}

onMounted(() => {
  loadData();
  loadDomains();
});
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
</style>
