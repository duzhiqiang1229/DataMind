<template>
  <div class="cube-modeling">
    <div class="workbench">
      <!-- 左侧：实体列表 -->
      <div class="panel list-panel">
        <el-tabs v-model="entityTab" class="entity-tabs">
          <el-tab-pane label="Cube" name="cube">
            <div class="panel-toolbar">
              <el-input v-model="cubeKeyword" placeholder="搜索 Cube" :prefix-icon="Search" clearable size="small" @input="filterCubes" />
              <el-button type="primary" size="small" :icon="Plus" @click="newCube">新建</el-button>
            </div>
            <el-scrollbar class="entity-list">
              <div
                v-for="c in filteredCubes"
                :key="c.name"
                class="entity-item"
                :class="{ active: editorType === 'cube' && currentName === c.name }"
                @click="openCube(c.name)"
              >
                <div class="entity-name">{{ c.title || c.name }}</div>
                <div class="entity-sub">{{ c.name }} · {{ c.measures.length }} 度量 / {{ c.dimensions.length }} 维度</div>
              </div>
              <el-empty v-if="!loading && filteredCubes.length === 0" description="暂无 Cube" :image-size="48" />
            </el-scrollbar>
          </el-tab-pane>

          <el-tab-pane label="视图" name="view">
            <div class="panel-toolbar">
              <el-input v-model="viewKeyword" placeholder="搜索视图" :prefix-icon="Search" clearable size="small" @input="filterViews" />
              <el-button type="primary" size="small" :icon="Plus" @click="newView">新建</el-button>
            </div>
            <el-scrollbar class="entity-list">
              <div
                v-for="v in filteredViews"
                :key="v.name"
                class="entity-item"
                :class="{ active: editorType === 'view' && currentName === v.name }"
                @click="openView(v.name)"
              >
                <div class="entity-name">{{ v.title || v.name }}</div>
                <div class="entity-sub">{{ v.name }}</div>
              </div>
              <el-empty v-if="!loading && filteredViews.length === 0" description="暂无视图" :image-size="48" />
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 右侧：建模编辑器 -->
      <div class="panel editor-panel" v-loading="loading">
        <div class="editor-header">
          <span class="editor-title">{{ editorType === 'cube' ? 'Cube 建模' : '视图建模' }}</span>
          <div class="editor-actions">
            <el-button size="small" :icon="Refresh" :loading="refreshing" @click="handleRefresh">刷新模型</el-button>
          </div>
        </div>

        <!-- Cube 编辑器 -->
        <div v-if="editorType === 'cube'" class="cube-editor">
          <div class="form-grid">
            <el-form-item label="名称（编码）" required>
              <el-input v-model="cubeForm.name" :disabled="!!currentName" placeholder="如 orders，小写英文" />
            </el-form-item>
            <el-form-item label="中文标题">
              <el-input v-model="cubeForm.title" placeholder="如：订单" />
            </el-form-item>
            <el-form-item label="底层表">
              <el-input v-model="cubeForm.sql_table" placeholder="如 dwd.dwd_orders 或 orders" />
            </el-form-item>
            <el-form-item label="数据源">
              <el-select v-model="cubeForm.data_source" style="width: 100%;">
                <el-option label="default" value="default" />
              </el-select>
            </el-form-item>
          </div>

          <div class="section">
            <div class="section-header">
              <span>度量 Measure</span>
              <el-button link type="primary" :icon="Plus" @click="addRow('measures')">添加</el-button>
            </div>
            <el-table :data="cubeForm.measures" size="small" border>
              <el-table-column label="名称" min-width="120">
                <template #default="{ row }"><el-input v-model="row.name" size="small" placeholder="如 total_amount" /></template>
              </el-table-column>
              <el-table-column label="SQL" min-width="120">
                <template #default="{ row }"><el-input v-model="row.sql" size="small" placeholder="如 amount 或 *" /></template>
              </el-table-column>
              <el-table-column label="类型" width="140">
                <template #default="{ row }">
                  <el-select v-model="row.type" size="small" style="width: 100%;">
                    <el-option v-for="t in measureTypes" :key="t" :label="t" :value="t" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="标题" min-width="120">
                <template #default="{ row }"><el-input v-model="row.title" size="small" placeholder="如：支付金额" /></template>
              </el-table-column>
              <el-table-column width="56" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" :icon="Delete" @click="removeRow('measures', $index)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="section">
            <div class="section-header">
              <span>维度 Dimension</span>
              <el-button link type="primary" :icon="Plus" @click="addRow('dimensions')">添加</el-button>
            </div>
            <el-table :data="cubeForm.dimensions" size="small" border>
              <el-table-column label="名称" min-width="120">
                <template #default="{ row }"><el-input v-model="row.name" size="small" placeholder="如 city" /></template>
              </el-table-column>
              <el-table-column label="SQL" min-width="120">
                <template #default="{ row }"><el-input v-model="row.sql" size="small" placeholder="如 city" /></template>
              </el-table-column>
              <el-table-column label="类型" width="120">
                <template #default="{ row }">
                  <el-select v-model="row.type" size="small" style="width: 100%;">
                    <el-option v-for="t in dimensionTypes" :key="t" :label="t" :value="t" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="标题" min-width="120">
                <template #default="{ row }"><el-input v-model="row.title" size="small" placeholder="如：城市" /></template>
              </el-table-column>
              <el-table-column label="主键" width="70" align="center">
                <template #default="{ row }"><el-checkbox v-model="row.primary_key" /></template>
              </el-table-column>
              <el-table-column width="56" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" :icon="Delete" @click="removeRow('dimensions', $index)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="section">
            <div class="section-header">
              <span>常用条件 Segment</span>
              <el-button link type="primary" :icon="Plus" @click="addRow('segments')">添加</el-button>
            </div>
            <el-table :data="cubeForm.segments" size="small" border>
              <el-table-column label="名称" min-width="130">
                <template #default="{ row }"><el-input v-model="row.name" size="small" placeholder="如 paid_orders" /></template>
              </el-table-column>
              <el-table-column label="SQL 条件" min-width="200">
                <template #default="{ row }"><el-input v-model="row.sql" size="small" placeholder="如 status = 'paid'" /></template>
              </el-table-column>
              <el-table-column label="标题" min-width="120">
                <template #default="{ row }"><el-input v-model="row.title" size="small" placeholder="如：已支付订单" /></template>
              </el-table-column>
              <el-table-column width="56" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" :icon="Delete" @click="removeRow('segments', $index)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="section">
            <div class="section-header">
              <span>实体关系 Join</span>
              <el-button link type="primary" :icon="Plus" @click="addRow('joins')">添加</el-button>
            </div>
            <el-table :data="cubeForm.joins" size="small" border>
              <el-table-column label="目标 Cube" min-width="140">
                <template #default="{ row }">
                  <el-select v-model="row.name" filterable size="small" style="width: 100%;">
                    <el-option v-for="c in filteredCubes" :key="c.name" :label="c.name" :value="c.name" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="关系" width="130">
                <template #default="{ row }">
                  <el-select v-model="row.relationship" size="small" style="width: 100%;">
                    <el-option label="belongsTo（多对一）" value="belongsTo" />
                    <el-option label="hasMany（一对多）" value="hasMany" />
                    <el-option label="hasOne（一对一）" value="hasOne" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="SQL 条件" min-width="200">
                <template #default="{ row }"><el-input v-model="row.sql" size="small" placeholder="如 ${CUBE}.user_id = ${Users}.id" /></template>
              </el-table-column>
              <el-table-column width="56" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" :icon="Delete" @click="removeRow('joins', $index)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="editor-footer">
            <el-button type="primary" :loading="saving" @click="handleSaveCube">保存并重启 Cube</el-button>
            <el-button v-if="currentName" type="danger" plain @click="handleDeleteCube">删除此 Cube</el-button>
            <span class="footer-hint">保存后自动重启 cube-server 容器使模型生效</span>
          </div>
        </div>

        <!-- View 编辑器 -->
        <div v-else class="view-editor">
          <div class="form-grid">
            <el-form-item label="名称" required>
              <el-input v-model="viewForm.name" :disabled="!!currentName" placeholder="如 orders_view" />
            </el-form-item>
            <el-form-item label="中文标题">
              <el-input v-model="viewForm.title" placeholder="如：订单视图" />
            </el-form-item>
          </div>

          <div class="section">
            <div class="section-header">
              <span>暴露的 Cube（join_path + includes）</span>
              <el-button link type="primary" :icon="Plus" @click="addViewCube">添加</el-button>
            </div>
            <el-table :data="viewForm.cubes" size="small" border>
              <el-table-column label="join_path" min-width="200">
                <template #default="{ row }">
                  <el-select v-model="row.join_path" filterable allow-create size="small" style="width: 100%;">
                    <el-option v-for="c in filteredCubes" :key="c.name" :label="c.name" :value="c.name" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="includes（度量/维度）" min-width="260">
                <template #default="{ row }">
                  <el-select v-model="row.includes" multiple filterable allow-create size="small" style="width: 100%;" placeholder="输入成员名称回车">
                    <el-option
                      v-for="m in membersOf(row.join_path)"
                      :key="m"
                      :label="m"
                      :value="m"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column width="56" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" :icon="Delete" @click="viewForm.cubes.splice($index, 1)" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="editor-footer">
            <el-button type="primary" :loading="saving" @click="handleSaveView">保存并重启 Cube</el-button>
            <el-button v-if="currentName" type="danger" plain @click="handleDeleteView">删除此视图</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { Plus, Search, Refresh, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { cubeModelApi } from "@/api";

const loading = ref(false);
const saving = ref(false);
const refreshing = ref(false);
const entityTab = ref("cube");
const editorType = ref<"cube" | "view">("cube");
const currentName = ref("");

const cubes = ref<any[]>([]);
const views = ref<any[]>([]);
const cubeKeyword = ref("");
const viewKeyword = ref("");

const measureTypes = ["count", "sum", "avg", "min", "max", "countDistinct"];
const dimensionTypes = ["string", "number", "time", "boolean"];

const filteredCubes = computed(() => {
  const kw = cubeKeyword.value.trim().toLowerCase();
  if (!kw) return cubes.value;
  return cubes.value.filter((c) => (c.name + (c.title || "")).toLowerCase().includes(kw));
});
const filteredViews = computed(() => {
  const kw = viewKeyword.value.trim().toLowerCase();
  if (!kw) return views.value;
  return views.value.filter((v) => (v.name + (v.title || "")).toLowerCase().includes(kw));
});

function membersOf(joinPath: string): string[] {
  const cube = cubes.value.find((c) => c.name === joinPath);
  if (!cube) return [];
  return [
    ...(cube.measures || []).map((m: any) => m.name),
    ...(cube.dimensions || []).map((d: any) => d.name),
  ];
}

function filterCubes() {}
function filterViews() {}

const emptyCube = () => ({
  name: "",
  title: "",
  sql_table: "",
  sql: "",
  data_source: "default",
  joins: [] as any[],
  dimensions: [] as any[],
  measures: [{ name: "count", sql: "*", type: "count", title: "计数" }] as any[],
  segments: [] as any[],
});
const cubeForm = reactive<any>(emptyCube());

const emptyView = () => ({
  name: "",
  title: "",
  cubes: [{ join_path: "", includes: [] as string[] }] as any[],
});
const viewForm = reactive<any>(emptyView());

async function loadEntities() {
  loading.value = true;
  try {
    const res = await cubeModelApi.entities();
    cubes.value = res.cubes || [];
    views.value = res.views || [];
  } catch {
    // handled
  } finally {
    loading.value = false;
  }
}

function newCube() {
  editorType.value = "cube";
  currentName.value = "";
  Object.assign(cubeForm, emptyCube());
}

async function openCube(name: string) {
  editorType.value = "cube";
  currentName.value = name;
  try {
    const cube = await cubeModelApi.getCube(name);
    Object.assign(cubeForm, {
      name: cube.name || "",
      title: cube.title || "",
      sql_table: cube.sql_table || "",
      sql: cube.sql || "",
      data_source: cube.data_source || "default",
      joins: cube.joins || [],
      dimensions: cube.dimensions || [],
      measures: cube.measures || [],
      segments: cube.segments || [],
    });
  } catch {
    ElMessage.error("加载 Cube 失败");
  }
}

function addRow(section: string) {
  const defs: Record<string, any> = {
    measures: { name: "", sql: "", type: "sum", title: "" },
    dimensions: { name: "", sql: "", type: "string", title: "", primary_key: false },
    segments: { name: "", sql: "", title: "" },
    joins: { name: "", relationship: "belongsTo", sql: "" },
  };
  cubeForm[section].push({ ...defs[section] });
}

function removeRow(section: string, index: number) {
  cubeForm[section].splice(index, 1);
}

async function handleSaveCube() {
  if (!cubeForm.name.trim()) {
    ElMessage.warning("请输入 Cube 名称");
    return;
  }
  saving.value = true;
  try {
    const res = await cubeModelApi.saveCube({
      name: cubeForm.name,
      title: cubeForm.title,
      sql_table: cubeForm.sql_table,
      sql: cubeForm.sql,
      data_source: cubeForm.data_source,
      joins: cubeForm.joins,
      dimensions: cubeForm.dimensions,
      measures: cubeForm.measures,
      segments: cubeForm.segments,
    });
    ElMessage.success(`Cube 已保存，${res.refresh?.message || "模型已生效"}`);
    await loadEntities();
    currentName.value = cubeForm.name;
  } catch (e: any) {
    ElMessage.error(e?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleDeleteCube() {
  await ElMessageBox.confirm(`确认删除 Cube "${currentName.value}"？将同时删除模型文件。`, "删除确认", { type: "warning" });
  try {
    await cubeModelApi.deleteCube(currentName.value);
    ElMessage.success("已删除并重启 Cube");
    newCube();
    await loadEntities();
  } catch {
    // handled
  }
}

function newView() {
  editorType.value = "view";
  currentName.value = "";
  Object.assign(viewForm, emptyView());
}

async function openView(name: string) {
  editorType.value = "view";
  currentName.value = name;
  const v = views.value.find((x) => x.name === name);
  if (v) {
    Object.assign(viewForm, {
      name: v.name || "",
      title: v.title || "",
      cubes: v.cubes || [],
    });
  }
}

function addViewCube() {
  viewForm.cubes.push({ join_path: "", includes: [] });
}

async function handleSaveView() {
  if (!viewForm.name.trim()) {
    ElMessage.warning("请输入视图名称");
    return;
  }
  saving.value = true;
  try {
    const res = await cubeModelApi.saveView({
      name: viewForm.name,
      title: viewForm.title,
      cubes: viewForm.cubes,
    });
    ElMessage.success(`视图已保存，${res.refresh?.message || "模型已生效"}`);
    await loadEntities();
    currentName.value = viewForm.name;
  } catch (e: any) {
    ElMessage.error(e?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleDeleteView() {
  await ElMessageBox.confirm(`确认删除视图 "${currentName.value}"？`, "删除确认", { type: "warning" });
  try {
    await cubeModelApi.deleteView(currentName.value);
    ElMessage.success("已删除并重启 Cube");
    newView();
    await loadEntities();
  } catch {
    // handled
  }
}

async function handleRefresh() {
  refreshing.value = true;
  try {
    const res = await cubeModelApi.refresh();
    ElMessage.success(res?.message || "模型已刷新");
    await loadEntities();
  } catch {
    // handled
  } finally {
    refreshing.value = false;
  }
}

onMounted(async () => {
  await loadEntities();
  if (cubes.value.length) {
    openCube(cubes.value[0].name);
  }
});
</script>

<style lang="scss" scoped>
.workbench {
  display: flex;
  gap: 12px;
  height: calc(100vh - 160px);
  min-height: 520px;
}

.panel {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-lighter);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-panel {
  width: 300px;
  flex-shrink: 0;

  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    min-height: 0;
  }
}

.entity-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;

  :deep(.el-tab-pane) {
    height: 100%;
    display: flex;
    flex-direction: column;
  }
}

.panel-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.entity-list {
  flex: 1;
  padding: 6px 8px 10px;
}

.entity-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  border-left: 3px solid transparent;
  transition: background-color 0.15s;

  &:hover {
    background: var(--el-fill-color-light);
  }

  &.active {
    background: var(--el-color-primary-light-9);
    border-left-color: var(--el-color-primary);
  }

  .entity-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .entity-sub {
    margin-top: 2px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.editor-panel {
  flex: 1;
  min-width: 0;
  padding: 14px 16px;
  overflow-y: auto;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;

  .editor-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.section {
  margin-top: 16px;

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin-bottom: 8px;
  }
}

.editor-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--el-border-color-lighter);

  .footer-hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
</style>
