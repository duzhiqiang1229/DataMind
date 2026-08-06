<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>角色管理</span>
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增角色</el-button>
      </div>
    </template>

    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="role_name" label="角色名称" />
      <el-table-column prop="role_code" label="编码" width="150" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button text type="primary" @click="handlePermissions(row)">权限</el-button>
          <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新增角色'" width="500px" @close="clearForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="编码" prop="role_code">
          <el-input v-model="form.role_code" placeholder="如 data_engineer" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="名称" prop="role_name">
          <el-input v-model="form.role_name" placeholder="角色名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="角色描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="permDrawerVisible" :title="`权限分配 - ${currentRoleName}`" size="500px" direction="rtl">
      <el-checkbox-group v-model="selectedPermissions" v-loading="permLoading">
        <el-checkbox
          v-for="p in allPermissions"
          :key="p.id"
          :value="p.id"
          style="display: block; margin-bottom: 8px;"
        >
          <el-tag size="small" type="info">{{ p.resource }}:{{ p.action }}</el-tag>
          {{ p.permission_name }}
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="permDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePermissions">保存</el-button>
      </template>
    </el-drawer>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { roleApi } from "@/api";

const loading = ref(false);
const tableData = ref<any[]>([]);

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const permDrawerVisible = ref(false);
const permLoading = ref(false);
const currentRoleId = ref("");
const currentRoleName = ref("");
const allPermissions = ref<any[]>([]);
const selectedPermissions = ref<string[]>([]);

const defaultForm = { role_code: "", role_name: "", description: "" };
const form = reactive({ ...defaultForm });

const formRules = {
  role_code: [{ required: true, message: "请输入编码", trigger: "blur" }],
  role_name: [{ required: true, message: "请输入名称", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await roleApi.list();
    tableData.value = res || [];
  } catch { /* handled */ } finally {
    loading.value = false;
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
    role_code: row.role_code,
    role_name: row.role_name,
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
        await roleApi.update(editId.value, form);
        ElMessage.success("更新成功");
      } else {
        await roleApi.create(form);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch { /* handled */ } finally {
      submitting.value = false;
    }
  });
}

async function handlePermissions(row: any) {
  currentRoleId.value = row.id;
  currentRoleName.value = row.role_name;
  permDrawerVisible.value = true;
  permLoading.value = true;
  try {
    const [perms, roles] = await Promise.all([roleApi.listPermissions(), roleApi.list()]);
    allPermissions.value = perms || [];
    const role = (roles || []).find((r: any) => r.id === row.id);
    selectedPermissions.value = (role?.permissions || []).map((p: any) => p.id);
  } catch { /* handled */ } finally {
    permLoading.value = false;
  }
}

async function handleSavePermissions() {
  try {
    await roleApi.assignPermissions(currentRoleId.value, selectedPermissions.value);
    ElMessage.success("权限保存成功");
    permDrawerVisible.value = false;
    loadData();
  } catch { /* handled */ }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除角色 "${row.role_name}"?`, "提示", { type: "warning" });
  await roleApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function clearForm() {
  formRef.value?.resetFields();
  Object.assign(form, defaultForm);
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
