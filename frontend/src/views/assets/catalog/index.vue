<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据目录</span>
          <el-input v-model="searchQuery" placeholder="搜索数据资产" style="width: 250px;" :prefix-icon="Search" clearable @keyup.enter="handleSearch" />
        </div>
      </template>

      <el-alert v-if="!omHealthy && !loading" type="warning" :closable="false" style="margin-bottom: 16px;">
        OpenMetadata 组件未连接，请在「系统管理 → 组件配置」中配置 OpenMetadata 组件。
      </el-alert>

      <el-row :gutter="16" v-if="searchResults.length > 0">
        <el-col :span="24">
          <h4>搜索结果</h4>
          <el-table :data="searchResults" border size="small" style="margin-bottom: 16px;">
            <el-table-column prop="name" label="名称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="fullyQualifiedName" label="全限定名" min-width="200" show-overflow-tooltip />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="viewLineage(row)">血缘</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="6">
          <el-card shadow="never" class="db-list">
            <template #header>数据库</template>
            <el-menu @select="handleDbSelect" :default-active="currentDb">
              <el-menu-item v-for="db in databases" :key="db.fullyQualifiedName" :index="db.fullyQualifiedName">
                {{ db.name }}
              </el-menu-item>
            </el-menu>
            <el-empty v-if="databases.length === 0" description="暂无数据" :image-size="60" />
          </el-card>
        </el-col>
        <el-col :span="18">
          <el-card shadow="never">
            <template #header>表 ({{ tables.length }})</template>
            <el-table :data="tables" v-loading="tableLoading" border size="small">
              <el-table-column prop="name" label="表名" width="180" />
              <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
              <el-table-column label="列数" width="80">
                <template #default="{ row }">{{ row.columns?.length || 0 }}</template>
              </el-table-column>
              <el-table-column label="标签" width="150">
                <template #default="{ row }">
                  <el-tag v-for="tag in (row.tags || []).slice(0, 3)" :key="tag.tagFQN" size="small" style="margin: 2px;">
                    {{ tag.tagFQN?.split('.')?.pop() || tag.name }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="viewLineage(row)">血缘</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!tableLoading && tables.length === 0" description="选择左侧数据库查看表" />
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 血缘关系对话框 -->
    <el-dialog v-model="lineageDialogVisible" title="血缘关系" width="800px">
      <div v-loading="lineageLoading">
        <pre v-if="lineageData" class="lineage-content">{{ JSON.stringify(lineageData, null, 2) }}</pre>
        <el-empty v-else description="暂无血缘数据" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Search } from "@element-plus/icons-vue";
import { openmetadataApi } from "@/api";

const loading = ref(false);
const tableLoading = ref(false);
const lineageLoading = ref(false);
const omHealthy = ref(false);
const databases = ref<any[]>([]);
const tables = ref<any[]>([]);
const currentDb = ref("");
const searchQuery = ref("");
const searchResults = ref<any[]>([]);
const lineageDialogVisible = ref(false);
const lineageData = ref<any>(null);

async function loadData() {
  loading.value = true;
  try {
    const [health] = await Promise.all([openmetadataApi.health()]);
    omHealthy.value = health?.healthy || false;

    if (omHealthy.value) {
      const dbs = await openmetadataApi.databases();
      databases.value = dbs || [];
      if (databases.value.length > 0) {
        currentDb.value = databases.value[0].fullyQualifiedName;
        await loadTables(currentDb.value);
      }
    }
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

async function loadTables(dbFqn: string) {
  tableLoading.value = true;
  try {
    const res = await openmetadataApi.tables(dbFqn);
    tables.value = res || [];
  } catch { /* handled */ } finally {
    tableLoading.value = false;
  }
}

function handleDbSelect(index: string) {
  currentDb.value = index;
  loadTables(index);
}

async function handleSearch() {
  if (!searchQuery.value.trim()) return;
  try {
    const res = await openmetadataApi.search(searchQuery.value);
    searchResults.value = res || [];
  } catch { /* handled */ }
}

async function viewLineage(row: any) {
  lineageDialogVisible.value = true;
  lineageLoading.value = true;
  lineageData.value = null;
  try {
    const fqn = row.fullyQualifiedName || row.name;
    const res = await openmetadataApi.lineage(fqn);
    lineageData.value = res;
  } catch { /* handled */ } finally {
    lineageLoading.value = false;
  }
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.db-list { max-height: 500px; overflow-y: auto; }
.lineage-content {
  max-height: 500px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4;
  padding: 12px; border-radius: 4px; font-family: monospace; font-size: 13px;
  white-space: pre-wrap; word-break: break-all;
}
</style>
