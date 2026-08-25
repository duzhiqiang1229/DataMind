<template>
  <div class="metrics-definitions">
    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>指标定义</span>
          <div>
            <el-button @click="openCategoryManager">分类管理</el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate">新建指标</el-button>
          </div>
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
        <el-select v-model="search.metric_type" placeholder="指标类型" clearable style="width: 140px;" @change="handleSearch">
          <el-option label="原子指标" value="atomic" />
          <el-option label="派生指标" value="derived" />
          <el-option label="复合指标" value="composite" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
      </div>

      <el-table :data="definitions" v-loading="loading" border>
        <el-table-column prop="metric_name" label="指标名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="指标类型" width="100">
          <template #default="{ row }"><el-tag size="small" :type="metricTypeTag(row.metric_type)">{{ metricTypeLabel(row.metric_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="分类" min-width="130">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ categoryName(row.category_id) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="业务域" min-width="120">
          <template #default="{ row }">{{ row.business_domain || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="90">
          <template #default="{ row }">{{ row.unit || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'published' || row.status === 'active' ? 'success' : 'info'">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
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
            <el-form-item label="指标类型" prop="metric_type">
              <el-select v-model="form.metric_type" style="width: 100%;">
                <el-option label="原子指标" value="atomic" />
                <el-option label="派生指标" value="derived" />
                <el-option label="复合指标" value="composite" />
              </el-select>
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

    <el-dialog v-model="categoryManagerVisible" title="指标分类管理" width="780px">
      <div class="category-toolbar">
        <span class="category-hint">分类用于统一组织指标，在新建和编辑指标时选择。</span>
        <el-button type="primary" :icon="Plus" @click="openCategoryEdit()">新建分类</el-button>
      </div>
      <el-table :data="categories" v-loading="categoryLoading" border stripe>
        <el-table-column prop="category_name" label="分类名称" min-width="150" />
        <el-table-column prop="category_code" label="分类编码" min-width="150" />
        <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" align="right" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openCategoryEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteCategory(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!categoryLoading && !categories.length" description="暂无分类，请新建指标分类" />
    </el-dialog>

    <el-dialog v-model="categoryEditVisible" :title="categoryEditId ? '编辑分类' : '新建分类'" width="520px" append-to-body>
      <el-form ref="categoryFormRef" :model="categoryForm" :rules="categoryRules" label-width="90px">
        <el-form-item label="分类名称" prop="category_name">
          <el-input v-model="categoryForm.category_name" maxlength="100" placeholder="如：财务指标" />
        </el-form-item>
        <el-form-item label="分类编码" prop="category_code">
          <el-input v-model="categoryForm.category_code" maxlength="100" placeholder="如：finance" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="categoryForm.sort_order" :min="0" :max="9999" controls-position="right" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="categoryForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="categorySaving" @click="saveCategory">保存</el-button>
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
const search = reactive({ keyword: "", category_id: "", metric_type: "" });

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
const categoryManagerVisible = ref(false);
const categoryEditVisible = ref(false);
const categoryLoading = ref(false);
const categorySaving = ref(false);
const categoryEditId = ref("");
const categoryFormRef = ref<FormInstance>();
const categoryForm = reactive({ category_name: "", category_code: "", description: "", sort_order: 0 });
const categoryRules = {
  category_name: [{ required: true, message: "请输入分类名称", trigger: "blur" }],
  category_code: [
    { required: true, message: "请输入分类编码", trigger: "blur" },
    { pattern: /^[A-Za-z][A-Za-z0-9_-]*$/, message: "编码须以字母开头，只能包含字母、数字、下划线和短横线", trigger: "blur" },
  ],
};

const defaultForm = {
  metric_name: "",
  metric_type: "atomic",
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
  metric_type: [{ required: true, message: "请选择指标类型", trigger: "change" }],
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
      metric_type: search.metric_type || undefined,
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
  Object.assign(search, { keyword: "", category_id: "", metric_type: "" });
  pagination.page = 1;
  loadDefinitions();
}

function categoryName(id: string | null): string {
  if (!id) return "-";
  const c = categories.value.find((x) => x.id === id);
  return c ? c.category_name : "-";
}

function metricTypeLabel(value?: string): string {
  return ({ atomic: "原子指标", derived: "派生指标", composite: "复合指标" } as Record<string, string>)[value || "atomic"] || "原子指标";
}

function metricTypeTag(value?: string): "primary" | "success" | "warning" {
  return value === "derived" ? "warning" : value === "composite" ? "success" : "primary";
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
    metric_type: row.metric_type || "atomic",
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
        metric_type: form.metric_type || "atomic",
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
  categoryLoading.value = true;
  try {
    const res = await metricCategoryApi.list();
    categories.value = res || [];
  } catch {
    // handled
  } finally {
    categoryLoading.value = false;
  }
}

async function openCategoryManager() {
  categoryManagerVisible.value = true;
  await loadCategories();
}

function openCategoryEdit(row?: any) {
  categoryEditId.value = row?.id || "";
  Object.assign(categoryForm, {
    category_name: row?.category_name || "",
    category_code: row?.category_code || "",
    description: row?.description || "",
    sort_order: row?.sort_order || 0,
  });
  categoryEditVisible.value = true;
}

async function saveCategory() {
  if (!categoryFormRef.value) return;
  const valid = await categoryFormRef.value.validate().catch(() => false);
  if (!valid) return;
  categorySaving.value = true;
  try {
    const payload = {
      category_name: categoryForm.category_name.trim(),
      category_code: categoryForm.category_code.trim(),
      description: categoryForm.description.trim() || null,
      sort_order: categoryForm.sort_order || 0,
    };
    if (categoryEditId.value) await metricCategoryApi.update(categoryEditId.value, payload);
    else await metricCategoryApi.create(payload);
    ElMessage.success(categoryEditId.value ? "分类已更新" : "分类已创建");
    categoryEditVisible.value = false;
    await loadCategories();
  } finally {
    categorySaving.value = false;
  }
}

async function deleteCategory(row: any) {
  await ElMessageBox.confirm(
    `确认删除分类“${row.category_name}”？已关联指标将变为未分类。`,
    "删除分类",
    { type: "warning" },
  );
  await metricCategoryApi.delete(row.id);
  if (search.category_id === row.id) search.category_id = "";
  if (form.category_id === row.id) form.category_id = "";
  ElMessage.success("分类已删除");
  await Promise.all([loadCategories(), loadDefinitions()]);
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

.category-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.category-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
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
