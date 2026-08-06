<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Spark 任务</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新建任务</el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" border>
        <el-table-column prop="task_name" label="任务名称" />
        <el-table-column prop="task_code" label="编码" width="150" />
        <el-table-column prop="mode" label="模式" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.mode === 'pyspark' ? 'warning' : 'info'">
              {{ row.mode === 'pyspark' ? 'PySpark' : 'SQL' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_table" label="目标表" width="150" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleTrigger(row)">执行</el-button>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新建任务'" width="650px" @close="clearForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="form.task_name" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="任务编码" prop="task_code">
          <el-input v-model="form.task_code" placeholder="唯一编码" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="执行模式">
          <el-radio-group v-model="form.mode">
            <el-radio value="sql">Spark SQL</el-radio>
            <el-radio value="pyspark">PySpark</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="form.mode === 'sql' ? 'SQL文件路径' : '脚本路径'" prop="file_path">
          <el-input v-model="form.file_path" :placeholder="form.mode === 'sql' ? '/opt/spark/sql/transform.sql' : '/opt/spark/scripts/job.py'" />
        </el-form-item>
        <el-form-item label="目标库" prop="target_database">
          <el-input v-model="form.target_database" placeholder="如 dwd" />
        </el-form-item>
        <el-form-item label="目标表" prop="target_table">
          <el-input v-model="form.target_table" placeholder="如 dwd_user_fact" />
        </el-form-item>
        <el-form-item label="Spark Master">
          <el-input v-model="form.spark_config.master" placeholder="spark://spark-master:7077" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Executor内存">
              <el-input v-model="form.spark_config.executor_memory" placeholder="2g" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Executor核数">
              <el-input-number v-model="form.spark_config.executor_cores" :min="1" :max="32" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="调度Cron">
          <el-input v-model="form.schedule_cron" placeholder="如 0 2 * * * (每天2点执行)" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="任务描述" />
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
import { sparkApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

const loading = ref(false);
const tableData = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const defaultForm = {
  task_name: "",
  task_code: "",
  mode: "sql",
  file_path: "",
  target_database: "dwd",
  target_table: "",
  spark_config: {
    master: "spark://spark-master:7077",
    executor_memory: "2g",
    executor_cores: 2,
    num_executors: 3,
  },
  variables: {} as Record<string, any>,
  schedule_cron: "",
  description: "",
};

const form = reactive(JSON.parse(JSON.stringify(defaultForm)));

const formRules = {
  task_name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
  task_code: [{ required: true, message: "请输入任务编码", trigger: "blur" }],
  file_path: [{ required: true, message: "请输入文件路径", trigger: "blur" }],
  target_database: [{ required: true, message: "请输入目标库", trigger: "blur" }],
  target_table: [{ required: true, message: "请输入目标表", trigger: "blur" }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await sparkApi.list({ page: pagination.page, page_size: pagination.page_size });
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
    task_name: row.task_name || "",
    task_code: row.task_code || "",
    mode: row.mode || "sql",
    file_path: row.file_path || "",
    target_database: row.target_database || "dwd",
    target_table: row.target_table || "",
    spark_config: row.spark_config || JSON.parse(JSON.stringify(defaultForm.spark_config)),
    variables: row.variables || {},
    schedule_cron: row.schedule_cron || "",
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
        await sparkApi.update(editId.value, form);
        ElMessage.success("更新成功");
      } else {
        await sparkApi.create(form);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadData();
    } catch { /* handled */ } finally {
      submitting.value = false;
    }
  });
}

async function handleTrigger(row: any) {
  await ElMessageBox.confirm(`确认执行任务 "${row.task_name}"?`, "执行确认");
  try {
    const res = await sparkApi.trigger(row.id);
    ElMessage.success(`任务已触发，执行ID: ${res.dag_run_id}`);
    loadData();
  } catch { /* handled */ }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除任务 "${row.task_name}"?`, "提示", { type: "warning" });
  await sparkApi.delete(row.id);
  ElMessage.success("删除成功");
  loadData();
}

function clearForm() {
  formRef.value?.resetFields();
  Object.assign(form, JSON.parse(JSON.stringify(defaultForm)));
}

function statusTag(status: string): TagType {
  const map: Record<string, TagType> = { draft: "info", active: "success", paused: "warning", archived: "info" };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = { draft: "草稿", active: "启用", paused: "暂停", archived: "归档" };
  return map[status] || status;
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
