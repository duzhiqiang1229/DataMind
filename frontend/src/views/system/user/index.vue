<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>用户管理</span>
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增用户</el-button>
      </div>
    </template>

    <el-form :inline="true" class="search-form">
      <el-form-item label="关键词">
        <el-input v-model="searchKeyword" placeholder="用户名/姓名" clearable style="width: 180px;" @keyup.enter="loadData" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="searchStatus" placeholder="全部" clearable style="width: 100px;" @change="loadData">
          <el-option label="启用" value="active" />
          <el-option label="禁用" value="disabled" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="tableData" v-loading="loading" border>
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="full_name" label="姓名" width="100" />
      <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
      <el-table-column prop="department" label="部门" width="120" />
      <el-table-column label="角色" width="150">
        <template #default="{ row }">
          <el-tag v-for="role in row.roles" :key="role.id" size="small" style="margin-right: 4px;">
            {{ role.name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" width="180" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button text type="primary" @click="handleResetPassword(row)">重置密码</el-button>
          <el-button text type="warning" @click="handleToggleStatus(row)">
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="550px"
      @close="clearForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" placeholder="姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="邮箱" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" placeholder="手机号" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" placeholder="部门" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <el-form :model="resetForm" label-width="80px">
        <el-form-item label="用户">
          <span>{{ resetForm.username }}</span>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetForm.new_password" type="password" show-password placeholder="新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleResetSubmit">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, type FormInstance } from "element-plus";
import { userApi } from "@/api";

interface UserForm {
  username: string;
  password: string;
  full_name: string;
  email: string;
  phone: string;
  department: string;
}

const loading = ref(false);
const tableData = ref<any[]>([]);
const searchKeyword = ref("");
const searchStatus = ref("");
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const resetDialogVisible = ref(false);
const resetForm = reactive({ username: "", user_id: "", new_password: "" });

const defaultForm: UserForm = {
  username: "",
  password: "",
  full_name: "",
  email: "",
  phone: "",
  department: "",
};

const form = reactive<UserForm>({ ...defaultForm });

const formRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await userApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: searchKeyword.value || undefined,
      status: searchStatus.value || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch {
    // handled by interceptor
  } finally {
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
    username: row.username || "",
    password: "",
    full_name: row.full_name || "",
    email: row.email || "",
    phone: row.phone || "",
    department: row.department || "",
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
        const payload = {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone,
          department: form.department,
        };
        await userApi.update(editId.value, payload);
        ElMessage.success("更新成功");
      } else {
        await userApi.create(form);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch {
      // handled
    } finally {
      submitting.value = false;
    }
  });
}

function handleResetPassword(row: any) {
  resetForm.username = row.username;
  resetForm.user_id = row.id;
  resetForm.new_password = "";
  resetDialogVisible.value = true;
}

async function handleResetSubmit() {
  if (!resetForm.new_password || resetForm.new_password.length < 6) {
    ElMessage.warning("密码至少6位");
    return;
  }
  try {
    await userApi.resetPassword(resetForm.user_id, resetForm.new_password);
    ElMessage.success("密码重置成功");
    resetDialogVisible.value = false;
  } catch {
    // handled
  }
}

async function handleToggleStatus(row: any) {
  try {
    await userApi.toggleStatus(row.id);
    ElMessage.success(row.status === 'active' ? '已禁用' : '已启用');
    loadData();
  } catch {
    // handled
  }
}

function clearForm() {
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
