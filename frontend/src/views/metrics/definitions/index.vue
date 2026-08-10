<template>
  <div class="metrics-definitions">
    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>指标定义</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建指标</el-button>
        </div>
      </template>

      <div class="stat-row">
        <div class="stat-item">
          <div class="stat-num">{{ pagination.total }}</div>
          <div class="stat-label">指标总数</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">{{ categories.length }}</div>
          <div class="stat-label">指标分类</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">{{ cubeCount }}</div>
          <div class="stat-label">关联 Cube</div>
        </div>
      </div>

      <div class="search-bar">
        <el-input
          v-model="search.keyword"
          placeholder="搜索指标名称"
          clearable
          :prefix-icon="Search"
          style="width: 220px;"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="search.category_id" placeholder="分类" clearable filterable style="width: 150px;" @change="handleSearch">
          <el-option v-for="c in categories" :key="c.id" :label="c.category_name" :value="c.id" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
      </div>

      <el-table :data="definitions" v-loading="loading" border>
        <el-table-column prop="metric_name" label="指标名称" min-width="140" show-overflow-tooltip />
            <el-table-column prop="cube_name" label="Cube" width="150" show-overflow-tooltip />
            <el-table-column prop="cube_measure" label="度量" width="180" show-overflow-tooltip />
            <el-table-column label="来源表" width="170" show-overflow-tooltip>
              <template #default="{ row }">{{ cubeTable(row.cube_name) || '-' }}</template>
            </el-table-column>
            <el-table-column label="分类" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ categoryName(row.category_id) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="业务域" width="90">
          <template #default="{ row }">{{ row.business_domain || '-' }}</template>
        </el-table-column>
            <el-table-column prop="unit" label="单位" width="70">
              <template #default="{ row }">{{ row.unit || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'published' || row.status === 'active' ? 'success' : 'info'">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
        <el-table-column label="维度" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.dimensions || []).join(', ') || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" @click="goQuery(row)">查询</el-button>
            <el-button link :type="row.status === 'published' || row.status === 'active' ? 'warning' : 'success'" @click="handleToggleStatus(row)">
              {{ row.status === 'published' || row.status === 'active' ? '取消发布' : '发布' }}
            </el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, prev, pager, next, jumper"
        @current-change="loadDefinitions"
        style="margin-top: 16px; justify-content: flex-end;"
      />
    </el-card>

    <!-- 新建/编辑指标 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑指标' : '新建指标'" width="860px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="指标名称" prop="metric_name">
              <el-input v-model="form.metric_name" placeholder="如：应收金额" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Cube" prop="cube_name">
              <el-select v-model="form.cube_name" placeholder="选择 Cube" filterable style="width: 100%;" @change="onFormCubeChange">
                <el-option v-for="c in cubeList" :key="c.name" :label="c.title || c.name" :value="c.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="度量" prop="cube_measure">
              <el-select v-model="form.cube_measure" placeholder="选择度量" filterable style="width: 100%;">
                <el-option v-for="m in cubeMeasures" :key="m.name" :label="m.title || m.name" :value="m.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="form.category_id" placeholder="选择分类" clearable filterable style="width: 100%;">
                <el-option v-for="c in categories" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="维度">
              <el-select v-model="form.dimensions" multiple filterable placeholder="关联维度" style="width: 100%;">
                <el-option v-for="d in cubeDimensions" :key="d.name" :label="d.title || d.name" :value="d.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认时间维度">
              <el-select v-model="form.default_time_dimension" clearable filterable placeholder="趋势分析默认维度" style="width: 100%;">
                <el-option v-for="d in cubeTimeDimensions" :key="d.name" :label="d.title || d.name" :value="d.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务域">
              <el-input v-model="form.business_domain" placeholder="如：销售域" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位">
              <el-input v-model="form.unit" placeholder="如：元" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%;">
                <el-option label="草稿" value="draft" />
                <el-option label="已发布" value="published" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item v-if="selectedCubeInfo" label="来源信息">
              <div class="cube-info-line">
                <el-tag size="small" effect="plain">来源表：{{ selectedCubeInfo.sql_table || '未指定' }}</el-tag>
                <el-tag size="small" type="info" effect="plain">度量类型：{{ selectedCubeInfo.types || '-' }}</el-tag>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计算口径">
              <el-input v-model="form.calculation" type="textarea" :rows="2" placeholder="指标计算公式 / 口径说明" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="指标描述" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Plus, Search, RefreshLeft } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { cubeApi, cubeModelApi, metricDefinitionApi, metricCategoryApi } from "@/api";

const router = useRouter();
const route = useRoute();

const loading = ref(false);
const definitions = ref<any[]>([]);
const categories = ref<any[]>([]);
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const search = reactive({ keyword: "", category_id: "" });

const cubeCount = computed(() => {
  const set = new Set<string>();
  definitions.value.forEach((d) => d.cube_name && set.add(d.cube_name));
  return set.size;
});

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const editId = ref("");
const formRef = ref<FormInstance>();

const defaultForm = {
  metric_name: "",
  cube_name: "",
  cube_measure: "",
  category_id: "",
  dimensions: [] as string[],
  default_time_dimension: "",
  calculation: "",
  business_domain: "",
  unit: "",
  description: "",
  status: "draft",
};
const form = reactive<any>({ ...defaultForm });

const formRules = {
  metric_name: [{ required: true, message: "请输入指标名称", trigger: "blur" }],
  cube_name: [{ required: true, message: "请选择 Cube", trigger: "change" }],
  cube_measure: [{ required: true, message: "请选择度量", trigger: "change" }],
};

// Cube 元数据（供表单选择度量/维度）
const metaData = ref<any>(null);
const modelEntities = ref<any[]>([]);
const cubeList = computed(() => (metaData.value?.cubes || []) as any[]);

const cubeInfoMap = computed(() => {
  const map: Record<string, { sql_table: string; types: string }> = {};
  (modelEntities.value || []).forEach((c) => {
    const types = [...new Set((c.measures || []).map((m: any) => m.type).filter(Boolean))];
    map[c.name] = { sql_table: c.sql_table || "", types: types.join(" / ") };
  });
  return map;
});

function cubeTable(cubeName: string): string {
  return cubeInfoMap.value[cubeName]?.sql_table || "";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = { draft: "草稿", published: "已发布", active: "已发布" };
  return map[status] || status || "草稿";
}

async function loadMeta() {
  try {
    const meta = await cubeApi.meta().catch(() => null);
    if (meta) metaData.value = meta;
    const entities = await cubeModelApi.entities().catch(() => null);
    if (entities) modelEntities.value = entities.cubes || [];
  } catch {
    // handled
  }
}

const cubeMeasures = computed(() => {
  const c = cubeList.value.find((x: any) => x.name === form.cube_name);
  return (c?.measures || []) as any[];
});
const cubeDimensions = computed(() => {
  const c = cubeList.value.find((x: any) => x.name === form.cube_name);
  return (c?.dimensions || []) as any[];
});
const cubeTimeDimensions = computed(() =>
  cubeDimensions.value.filter((d: any) => d.type === "time"),
);
const selectedCubeInfo = computed(() => {
  if (!form.cube_name) return null;
  return cubeInfoMap.value[form.cube_name] || null;
});

function onFormCubeChange() {
  form.cube_measure = "";
  form.dimensions = [];
}

async function loadDefinitions() {
  loading.value = true;
  try {
    const res = await metricDefinitionApi.list({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: search.keyword || undefined,
      category_id: search.category_id || undefined,
    });
    definitions.value = res.items || [];
    pagination.total = res.total || 0;
  } catch {
    // handled
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  pagination.page = 1;
  loadDefinitions();
}

function handleReset() {
  Object.assign(search, { keyword: "", category_id: "" });
  pagination.page = 1;
  loadDefinitions();
}

function categoryName(id: string | null): string {
  if (!id) return "-";
  const c = categories.value.find((x) => x.id === id);
  return c ? c.category_name : "-";
}

function goQuery(row: any) {
  router.push({ path: "/metrics/query", query: { metric_id: row.id } });
}

function openCreate() {
  isEdit.value = false;
  editId.value = "";
  Object.assign(form, { ...defaultForm, dimensions: [] });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  isEdit.value = true;
  editId.value = row.id;
  Object.assign(form, {
    metric_name: row.metric_name || "",
    cube_name: row.cube_name || "",
    cube_measure: row.cube_measure || "",
    category_id: row.category_id || "",
    dimensions: row.dimensions || [],
    default_time_dimension: row.default_time_dimension || "",
    calculation: row.calculation || "",
    business_domain: row.business_domain || "",
    unit: row.unit || "",
    description: row.description || "",
    status: row.status === "active" ? "published" : row.status || "draft",
  });
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      const payload = {
        metric_name: form.metric_name,
        cube_name: form.cube_name,
        cube_measure: form.cube_measure,
        category_id: form.category_id || null,
        dimensions: form.dimensions,
        default_time_dimension: form.default_time_dimension || null,
        calculation: form.calculation || null,
        business_domain: form.business_domain || null,
        unit: form.unit || null,
        description: form.description || null,
        status: form.status || "draft",
      };
      if (isEdit.value) {
        await metricDefinitionApi.update(editId.value, payload);
        ElMessage.success("更新成功");
      } else {
        await metricDefinitionApi.create(payload);
        ElMessage.success("创建成功");
      }
      dialogVisible.value = false;
      loadDefinitions();
    } catch {
      // handled
    } finally {
      submitting.value = false;
    }
  });
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除指标 "${row.metric_name}"？`, "删除确认", { type: "warning" });
  try {
    await metricDefinitionApi.delete(row.id);
    ElMessage.success("删除成功");
    loadDefinitions();
  } catch {
    // handled
  }
}

async function handleToggleStatus(row: any) {
  const toPublished = row.status !== "published" && row.status !== "active";
  await ElMessageBox.confirm(
    toPublished
      ? `确认发布指标 "${row.metric_name}"？`
      : `确认将指标 "${row.metric_name}" 改为草稿？`,
    toPublished ? "发布确认" : "取消发布确认",
    { type: "warning" },
  );
  try {
    await metricDefinitionApi.update(row.id, { status: toPublished ? "published" : "draft" });
    ElMessage.success(toPublished ? "已发布" : "已改为草稿");
    loadDefinitions();
  } catch {
    // handled
  }
}

function resetForm() {
  formRef.value?.resetFields();
  Object.assign(form, { ...defaultForm, dimensions: [] });
}

async function loadCategories() {
  try {
    const res = await metricCategoryApi.list();
    categories.value = res || [];
  } catch {
    // handled
  }
}

onMounted(async () => {
  loadDefinitions();
  loadCategories();
  loadMeta();
  if (route.query.create === "1") {
    openCreate();
  }
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

.stat-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;

  .stat-item {
    flex: 1;
    max-width: 220px;
    padding: 14px 18px;
    border-radius: 8px;
    background: linear-gradient(135deg, var(--el-color-primary-light-9), #fff);
    border: 1px solid var(--el-color-primary-light-7);

    .stat-num {
      font-size: 26px;
      font-weight: 700;
      color: var(--el-color-primary);
      line-height: 1.2;
    }

    .stat-label {
      margin-top: 4px;
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
  }
}

.cube-info-line {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
