<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>发布管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新建发布</el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" border>
        <el-table-column prop="publish_name" label="发布名称" />
        <el-table-column prop="publish_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ typeLabel(row.publish_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_environment" label="环境" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="executed_at" label="执行时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleDetail(row)">详情</el-button>
            <el-button v-if="row.status === 'pending'" text type="success" @click="handleExecute(row)">执行</el-button>
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

    <!-- 新建发布对话框 -->
    <el-dialog v-model="dialogVisible" title="新建发布任务" width="550px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="发布名称" prop="publish_name">
          <el-input v-model="form.publish_name" placeholder="发布名称" />
        </el-form-item>
        <el-form-item label="发布类型" prop="publish_type">
          <el-select v-model="form.publish_type" style="width: 100%;">
            <el-option label="数据模型" value="model" />
            <el-option label="Spark任务" value="spark_task" />
            <el-option label="DataX任务" value="datax_task" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标环境">
          <el-select v-model="form.target_environment" style="width: 100%;">
            <el-option label="生产" value="production" />
            <el-option label="测试" value="staging" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="发布描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailDrawerVisible" title="发布详情" size="50%">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="发布名称">{{ currentTask?.publish_name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeLabel(currentTask?.publish_type) }}</el-descriptions-item>
        <el-descriptions-item label="环境">{{ currentTask?.target_environment }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(currentTask?.status) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentTask?.created_at }}</el-descriptions-item>
        <el-descriptions-item label="执行时间">{{ currentTask?.executed_at }}</el-descriptions-item>
      </el-descriptions>

      <h4 style="margin: 16px 0 8px;">发布记录</h4>
      <el-table :data="currentTask?.records || []" border size="small">
        <el-table-column prop="source_name" label="名称" />
        <el-table-column prop="source_type" label="类型" width="100" />
        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="resultTag(row.result)">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { publishApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const submitting = ref(false);
const formRef = ref<FormInstance>();

const detailDrawerVisible = ref(false);
const currentTask = ref<any>(null);

const form = reactive({
  publish_name: "",
  publish_type: "model",
  source_ids: [] as string[],
  target_environment: "production",
  description: "",
});

const formRules = {
  publish_name: [{ required: true, message: "请输入发布名称", trigger: "blur" }],
  publish_type: [{ required: true, message: "请选择类型", trigger: "change" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await publishApi.list({ page: pagination.page, page_size: pagination.page_size });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

function handleAdd() {
  Object.assign(form, { publish_name: "", publish_type: "model", source_ids: [], target_environment: "production", description: "" });
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      await publishApi.create(form);
      ElMessage.success("创建成功");
      dialogVisible.value = false;
      loadData();
    } catch { /* handled */ } finally {
      submitting.value = false;
    }
  });
}

async function handleDetail(row: any) {
  try {
    const res = await publishApi.detail(row.id);
    currentTask.value = res;
    detailDrawerVisible.value = true;
  } catch { /* handled */ }
}

async function handleExecute(row: any) {
  await ElMessageBox.confirm(`确认执行发布任务 "${row.publish_name}"?`, "执行确认");
  try {
    await publishApi.execute(row.id);
    ElMessage.success("执行完成");
    loadData();
  } catch { /* handled */ }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除发布任务 "${row.publish_name}"?`, "提示", { type: "warning" });
  await publishApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function typeLabel(type?: string) {
  const map: Record<string, string> = { model: "数据模型", spark_task: "Spark任务", datax_task: "DataX任务" };
  return map[type || ""] || type;
}

function statusTag(status: string): TagType {
  const map: Record<string, TagType> = { pending: "info", running: "warning", success: "success", failed: "danger" };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = { pending: "待执行", running: "执行中", success: "成功", failed: "失败" };
  return map[status] || status;
}

function resultTag(result: string): TagType {
  const map: Record<string, TagType> = { pending: "info", success: "success", failed: "danger" };
  return map[result] || "info";
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
