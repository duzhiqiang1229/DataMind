<template>
  <div class="asset-page">
    <div class="stat-grid">
      <el-card v-for="item in stats" :key="item.label" shadow="never" class="stat-card">
        <div class="stat-value">{{ item.value }}</div><div class="stat-label">{{ item.label }}</div>
      </el-card>
    </div>
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <div><div class="title">数据目录</div><div class="subtitle">统一浏览已采集的物理表、字段及其关联信息</div></div>
          <el-button type="primary" :icon="Refresh" :loading="syncing" @click="syncCatalog">同步元数据</el-button>
        </div>
      </template>
      <div class="toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索表名、FQN 或描述" :prefix-icon="Search" @keyup.enter="loadAssets" />
        <el-select v-model="datasourceId" clearable filterable placeholder="全部数据源" @change="loadAssets">
          <el-option v-for="ds in datasources" :key="ds.id" :label="ds.source_name" :value="ds.id" />
        </el-select>
        <el-button @click="loadAssets">查询</el-button>
      </div>
      <el-table v-loading="loading" :data="assets" border stripe @row-click="openDetail">
        <el-table-column prop="name" label="资产名称" min-width="190"><template #default="{ row }"><el-link type="primary">{{ row.name }}</el-link></template></el-table-column>
        <el-table-column prop="datasource_name" label="数据源" min-width="140" />
        <el-table-column prop="database_name" label="数据库" min-width="120" />
        <el-table-column prop="schema_name" label="Schema" min-width="110"><template #default="{ row }">{{ row.schema_name || '-' }}</template></el-table-column>
        <el-table-column prop="asset_type" label="类型" width="100" align="center"><template #default><el-tag size="small" effect="plain" type="success">物理表</el-tag></template></el-table-column>
        <el-table-column prop="column_count" label="字段数" width="90" align="right" />
        <el-table-column prop="last_synced_at" label="最近同步" min-width="170"><template #default="{ row }">{{ formatTime(row.last_synced_at) }}</template></el-table-column>
      </el-table>
      <div class="pagination"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" @current-change="loadAssets" @size-change="loadAssets" /></div>
    </el-card>
    <el-drawer v-model="drawerVisible" title="资产详情" size="68%">
      <div v-if="detail" v-loading="detailLoading" class="detail">
        <div class="detail-title">{{ detail.name }}</div><div class="detail-fqn">{{ detail.fqn }}</div>
        <el-descriptions :column="3" border class="descriptions">
          <el-descriptions-item label="数据源">{{ detail.datasource_name }}</el-descriptions-item><el-descriptions-item label="数据库">{{ detail.database_name || '-' }}</el-descriptions-item><el-descriptions-item label="Schema">{{ detail.schema_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="字段数">{{ detail.column_count }}</el-descriptions-item><el-descriptions-item label="上游">{{ detail.upstream_count }}</el-descriptions-item><el-descriptions-item label="下游">{{ detail.downstream_count }}</el-descriptions-item>
        </el-descriptions>
        <h3>字段结构</h3>
        <el-table :data="detail.columns || []" border size="small" max-height="520">
          <el-table-column prop="ordinal_position" label="#" width="60" /><el-table-column prop="name" label="字段名" min-width="170" /><el-table-column prop="data_type" label="数据类型" min-width="150" />
          <el-table-column label="约束" width="140"><template #default="{ row }"><el-tag v-if="row.primary_key" size="small" type="warning">主键</el-tag><span v-else>{{ row.nullable ? '可空' : '非空' }}</span></template></el-table-column>
          <el-table-column prop="default_value" label="默认值" min-width="130"><template #default="{ row }">{{ row.default_value ?? '-' }}</template></el-table-column>
          <el-table-column prop="description" label="描述" min-width="180"><template #default="{ row }">{{ row.description || '-' }}</template></el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Refresh, Search } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { dataAssetApi, datasourceApi } from "@/api";

const loading = ref(false), syncing = ref(false), detailLoading = ref(false);
const assets = ref<any[]>([]), datasources = ref<any[]>([]), overview = ref<any>({});
const keyword = ref(""), datasourceId = ref("");
const page = ref(1), pageSize = ref(20), total = ref(0);
const drawerVisible = ref(false), detail = ref<any>(null);
const stats = computed(() => [
  { label: "有效资产", value: overview.value.assets || 0 }, { label: "字段总数", value: overview.value.columns || 0 },
  { label: "血缘关系", value: overview.value.lineage_edges || 0 }, { label: "质量规则", value: overview.value.quality_rules || 0 },
]);
async function loadAssets() { loading.value = true; try { const res: any = await dataAssetApi.catalog({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined, datasource_id: datasourceId.value || undefined }); assets.value = res.items || []; total.value = res.total || 0; } finally { loading.value = false; } }
async function loadOverview() { overview.value = await dataAssetApi.overview(); }
async function syncCatalog() { syncing.value = true; try { const result: any = await dataAssetApi.sync(datasourceId.value || undefined); if (result.errors?.length) ElMessage.warning(`同步完成，${result.errors.length} 个数据源失败`); else ElMessage.success(`已同步 ${result.tables} 张表、${result.columns} 个字段`); await Promise.all([loadAssets(), loadOverview()]); } finally { syncing.value = false; } }
async function openDetail(row: any) { drawerVisible.value = true; detailLoading.value = true; try { detail.value = await dataAssetApi.detail(row.id); } finally { detailLoading.value = false; } }
function formatTime(value: string) { return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"; }
onMounted(async () => { const ds: any = await datasourceApi.list({ page: 1, page_size: 100, status: "active" }); datasources.value = ds.items || []; await Promise.all([loadAssets(), loadOverview()]); });
</script>

<style scoped lang="scss">
.asset-page { padding: 16px; }.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }.stat-card { .stat-value { font-size: 28px; font-weight: 650; color: var(--el-color-primary); } .stat-label { color: var(--el-text-color-secondary); margin-top: 4px; } }.header { display: flex; align-items: center; justify-content: space-between; }.title { font-size: 18px; font-weight: 600; }.subtitle, .detail-fqn { color: var(--el-text-color-secondary); font-size: 13px; margin-top: 5px; }.toolbar { display: grid; grid-template-columns: minmax(260px, 1fr) 220px auto; gap: 10px; margin-bottom: 14px; }.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }.detail-title { font-size: 22px; font-weight: 650; }.descriptions { margin: 18px 0 22px; }@media (max-width: 900px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
