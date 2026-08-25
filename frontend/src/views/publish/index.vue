<template>
  <div class="publish-page">
    <!-- Top toolbar -->
    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <el-button type="primary" :icon="Plus" @click="handleAdd">新建发布</el-button>
        <div class="toolbar-right">
          <el-select
            v-model="filterType"
            placeholder="发布类型"
            clearable
            style="width: 160px"
            @change="handleFilterChange"
          >
            <el-option label="数据模型" value="model" />
          </el-select>
          <el-button type="primary" @click="handleFilterChange">查询</el-button>
          <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="content-row">
      <!-- Left: task list -->
      <el-col :span="10">
        <el-card class="list-card" shadow="never">
          <template #header>
            <span class="card-title">发布任务列表</span>
          </template>
          <el-table
            :data="tableData"
            v-loading="loading"
            border
            highlight-current-row
            @row-click="handleRowClick"
            :row-class-name="rowClassName"
          >
            <el-table-column prop="publish_name" label="名称" min-width="140" />
            <el-table-column prop="publish_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="typeTag(row.publish_type)">
                  {{ typeLabel(row.publish_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="statusTag(row.status)">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :total="pagination.total"
            layout="total, prev, pager, next"
            @current-change="loadData"
            small
            style="margin-top: 12px; justify-content: flex-end"
          />
        </el-card>
      </el-col>

      <!-- Right: detail panel -->
      <el-col :span="14">
        <el-card class="detail-card" shadow="never">
          <template #header>
            <div class="detail-header">
              <span class="card-title">发布详情</span>
              <div class="detail-actions">
                <el-button
                  v-if="currentTask && currentTask.status === 'pending'"
                  type="success"
                  :icon="VideoPlay"
                  :loading="executing"
                  @click="handleExecute"
                >
                  执行
                </el-button>
                <el-button :icon="Refresh" @click="refreshDetail">刷新</el-button>
              </div>
            </div>
          </template>

          <template v-if="currentTask">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="发布名称">{{ currentTask.publish_name }}</el-descriptions-item>
              <el-descriptions-item label="发布类型">
                <el-tag size="small" :type="typeTag(currentTask.publish_type)">
                  {{ typeLabel(currentTask.publish_type) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="目标环境">{{ currentTask.target_environment }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag size="small" :type="statusTag(currentTask.status)">
                  {{ statusLabel(currentTask.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDateTime(currentTask.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="执行时间">{{ formatDateTime(currentTask.executed_at) }}</el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ currentTask.description || "-" }}</el-descriptions-item>
            </el-descriptions>

            <h4 class="records-title">发布对象列表</h4>
            <el-table :data="currentTask.records || []" border size="small">
              <el-table-column prop="source_name" label="对象名称" min-width="180" />
              <el-table-column prop="source_type" label="对象类型" width="100" />
              <el-table-column prop="result" label="结果" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="resultTag(row.result)">{{ row.result || "-" }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
            </el-table>
          </template>

          <el-empty v-else description="请从左侧选择发布任务" />
        </el-card>
      </el-col>
    </el-row>

    <!-- New publish dialog -->
    <el-dialog v-model="dialogVisible" title="新建发布任务" width="550px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="发布名称" prop="publish_name">
          <el-input v-model="form.publish_name" placeholder="发布名称" />
        </el-form-item>
        <el-form-item label="发布类型" prop="publish_type">
          <el-select v-model="form.publish_type" style="width: 100%">
            <el-option label="数据模型" value="model" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标环境">
          <el-select v-model="form.target_environment" style="width: 100%">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Plus, Refresh, RefreshLeft, VideoPlay } from "@element-plus/icons-vue";
import { formatDateTime } from "@/utils/format";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { publishApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const filterType = ref<string>("");

const currentTask = ref<any>(null);
const executing = ref(false);

const dialogVisible = ref(false);
const submitting = ref(false);
const formRef = ref<FormInstance>();

const form = reactive({
  publish_name: "",
  publish_type: "model",
  target_environment: "production",
  description: "",
});

const formRules = {
  publish_name: [{ required: true, message: "请输入发布名称", trigger: "blur" }],
  publish_type: [{ required: true, message: "请选择类型", trigger: "change" }],
};

function rowClassName({ row }: { row: any }) {
  return currentTask.value && row.id === currentTask.value.id ? "selected-row" : "";
}

async function loadData() {
  loading.value = true;
  try {
    const res = await publishApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      publish_type: filterType.value || undefined,
    });
    tableData.value = res.items || [];
    pagination.total = res.total || 0;
    // auto-select first task
    if (tableData.value.length > 0) {
      await selectTask(tableData.value[0]);
    } else {
      currentTask.value = null;
    }
  } catch {
    /* handled */
  } finally {
    loading.value = false;
  }
}

function handleFilterChange() {
  pagination.page = 1;
  loadData();
}

function handleReset() {
  filterType.value = "";
  pagination.page = 1;
  loadData();
}

async function selectTask(row: any) {
  try {
    const res = await publishApi.detail(row.id);
    currentTask.value = res;
  } catch {
    /* handled */
  }
}

function handleRowClick(row: any) {
  selectTask(row);
}

async function refreshDetail() {
  if (!currentTask.value) return;
  try {
    const res = await publishApi.detail(currentTask.value.id);
    currentTask.value = res;
    ElMessage.success("已刷新");
  } catch {
    /* handled */
  }
}

function handleAdd() {
  Object.assign(form, {
    publish_name: "",
    publish_type: "model",
    target_environment: "production",
    description: "",
  });
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
    } catch {
      /* handled */
    } finally {
      submitting.value = false;
    }
  });
}

async function handleExecute() {
  if (!currentTask.value) return;
  await ElMessageBox.confirm(
    `确认执行发布任务 "${currentTask.value.publish_name}"?`,
    "执行确认"
  );
  executing.value = true;
  try {
    const res = await publishApi.execute(currentTask.value.id);
    currentTask.value = res;
    ElMessage.success("执行完成");
    // refresh list to reflect updated status
    loadData();
  } catch {
    /* handled */
  } finally {
    executing.value = false;
  }
}

function typeLabel(type?: string) {
  const map: Record<string, string> = {
    model: "数据模型",
  };
  return map[type || ""] || type || "";
}

function typeTag(type?: string): TagType {
  const map: Record<string, TagType> = {
    model: "primary",
  };
  return map[type || ""] || "info";
}

function statusTag(status: string): TagType {
  const map: Record<string, TagType> = {
    pending: "info",
    running: "warning",
    success: "success",
    failed: "danger",
  };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: "待执行",
    running: "执行中",
    success: "成功",
    failed: "失败",
  };
  return map[status] || status;
}

function resultTag(result: string): TagType {
  const map: Record<string, TagType> = {
    pending: "info",
    success: "success",
    failed: "danger",
  };
  return map[result] || "info";
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.publish-page {
  .toolbar-card {
    margin-bottom: 16px;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .content-row {
    align-items: stretch;
  }

  .list-card,
  .detail-card {
    height: 100%;
  }

  .card-title {
    font-weight: 600;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .detail-actions {
    display: flex;
    gap: 8px;
  }

  .records-title {
    margin: 16px 0 8px;
  }

  :deep(.selected-row) {
    cursor: pointer;
  }

  :deep(.el-table__row) {
    cursor: pointer;
  }
}
</style>
