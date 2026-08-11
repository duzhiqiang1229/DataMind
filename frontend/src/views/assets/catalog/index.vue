<template>
  <div class="asset-center" v-loading="loading">
    <div class="hero">
      <div>
        <h2>数据资产中心</h2>
        <p>由 OpenMetadata 提供统一目录、治理、质量与血缘信息</p>
      </div>
      <div class="hero-actions">
        <el-tag :type="omHealthy ? 'success' : 'danger'" effect="dark">
          {{ omHealthy ? "OpenMetadata 已连接" : "OpenMetadata 未连接" }}
        </el-tag>
        <el-button @click="openMetadata">打开 OpenMetadata</el-button>
        <el-button :icon="Refresh" circle @click="loadAll" />
      </div>
    </div>

    <el-alert v-if="!omHealthy && !loading" type="warning" :closable="false" show-icon>
      OpenMetadata 暂不可用，请确认服务已启动，并在「系统管理 → 组件配置」中检查连接。
    </el-alert>

    <el-row :gutter="16" class="summary-row">
      <el-col v-for="card in summaryCards" :key="card.label" :xs="12" :sm="8" :lg="4">
        <el-card shadow="hover" class="summary-card">
          <div class="summary-label">{{ card.label }}</div>
          <div class="summary-value">{{ card.value }}</div>
          <div class="summary-hint">{{ card.hint }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="workspace">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="资产目录" name="assets">
          <div class="toolbar">
            <el-input
              v-model="query"
              :prefix-icon="Search"
              placeholder="搜索名称、描述、标签或责任人"
              clearable
              @keyup.enter="searchAssets"
              @clear="searchAssets"
            />
            <el-select v-model="entityType" @change="searchAssets">
              <el-option v-for="item in entityTypes" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-button type="primary" :icon="Search" @click="searchAssets">搜索</el-button>
          </div>

          <el-table :data="assets" stripe @row-click="showDetail">
            <el-table-column label="类型" width="105">
              <template #default="{ row }">
                <el-tag :type="typeColor(row.entityType)" effect="plain">{{ typeLabel(row.entityType) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="资产" min-width="250">
              <template #default="{ row }">
                <div class="asset-name">{{ row.displayName || row.name }}</div>
                <div class="asset-fqn">{{ row.fullyQualifiedName }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip>
              <template #default="{ row }">{{ plainText(row.description) || "待补充" }}</template>
            </el-table-column>
            <el-table-column label="责任人" width="150">
              <template #default="{ row }">{{ ownerNames(row.owners) || "未分配" }}</template>
            </el-table-column>
            <el-table-column label="治理标签" min-width="180">
              <template #default="{ row }">
                <el-tag v-for="tag in (row.tags || []).slice(0, 2)" :key="tag.tagFQN" size="small" class="mini-tag">
                  {{ shortName(tag.tagFQN || tag.name) }}
                </el-tag>
                <span v-if="!row.tags?.length" class="muted">未标注</span>
              </template>
            </el-table-column>
            <el-table-column label="服务" width="130" show-overflow-tooltip>
              <template #default="{ row }">{{ row.service?.name || row.serviceType || "-" }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="showDetail(row)">详情</el-button>
                <el-button link type="primary" @click.stop="viewLineage(row)">血缘</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!assetLoading && !assets.length" description="暂无匹配资产" />
          <div class="pagination">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @current-change="loadAssets"
              @size-change="searchAssets"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="治理视图" name="governance">
          <el-row :gutter="16">
            <el-col :xs="24" :lg="8">
              <governance-list title="业务域" :items="governance.domains" empty="尚未建立业务域" />
            </el-col>
            <el-col :xs="24" :lg="8">
              <governance-list title="数据产品" :items="governance.dataProducts" empty="尚未建立数据产品" />
            </el-col>
            <el-col :xs="24" :lg="8">
              <governance-list title="术语表" :items="governance.glossaries" empty="尚未建立术语表" />
            </el-col>
          </el-row>
          <el-card shadow="never" class="governance-table">
            <template #header>业务术语（{{ governance.glossaryTerms.length }}）</template>
            <el-table :data="governance.glossaryTerms" stripe>
              <el-table-column prop="displayName" label="术语" min-width="160">
                <template #default="{ row }">{{ row.displayName || row.name }}</template>
              </el-table-column>
              <el-table-column prop="fullyQualifiedName" label="全限定名" min-width="220" show-overflow-tooltip />
              <el-table-column label="描述" min-width="260" show-overflow-tooltip>
                <template #default="{ row }">{{ plainText(row.description) || "待补充" }}</template>
              </el-table-column>
              <el-table-column label="审核人" min-width="160">
                <template #default="{ row }">{{ ownerNames(row.reviewers) || "未设置" }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="数据质量" name="quality">
          <div class="quality-head">
            <div><b>{{ quality.total || 0 }}</b><span>质量规则</span></div>
            <div class="success"><b>{{ statusCount("Success") }}</b><span>通过</span></div>
            <div class="danger"><b>{{ statusCount("Failed") }}</b><span>失败</span></div>
          </div>
          <el-table :data="quality.items" stripe>
            <el-table-column prop="name" label="检查项" min-width="180" />
            <el-table-column label="目标资产" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">{{ entityFromLink(row.entityLink) }}</template>
            </el-table-column>
            <el-table-column label="规则" min-width="180">
              <template #default="{ row }">{{ row.testDefinition?.displayName || row.testDefinition?.name || "-" }}</template>
            </el-table-column>
            <el-table-column label="最近结果" width="120">
              <template #default="{ row }">
                <el-tag :type="qualityColor(row.testCaseResult?.testCaseStatus)">
                  {{ qualityLabel(row.testCaseResult?.testCaseStatus) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="执行时间" width="180">
              <template #default="{ row }">{{ formatTime(row.testCaseResult?.timestamp) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!quality.items.length" description="暂无质量检查；可在 OpenMetadata 中创建测试规则" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-drawer v-model="detailVisible" size="54%" destroy-on-close>
      <template #header>
        <div>
          <div class="drawer-title">{{ selected?.displayName || selected?.name }}</div>
          <div class="asset-fqn">{{ selected?.fullyQualifiedName }}</div>
        </div>
      </template>
      <div v-loading="detailLoading" v-if="selected">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="资产类型">{{ typeLabel(selected.entityType || "table") }}</el-descriptions-item>
          <el-descriptions-item label="数据服务">{{ selected.service?.name || selected.serviceType || "-" }}</el-descriptions-item>
          <el-descriptions-item label="责任人">{{ ownerNames(selected.owners) || "未分配" }}</el-descriptions-item>
          <el-descriptions-item label="业务域">{{ ownerNames(selected.domains) || "未归属" }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ plainText(selected.description) || "待补充" }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-tags">
          <el-tag v-for="tag in selected.tags || []" :key="tag.tagFQN">{{ shortName(tag.tagFQN || tag.name) }}</el-tag>
          <span v-if="!selected.tags?.length" class="muted">尚未设置分类或术语标签</span>
        </div>

        <template v-if="selected.entityType === 'table' || selected.columns">
          <h3>字段结构（{{ selected.columns?.length || 0 }}）</h3>
          <el-table :data="selected.columns || []" max-height="360" stripe>
            <el-table-column prop="name" label="字段" min-width="150" />
            <el-table-column label="类型" width="140">
              <template #default="{ row }">{{ row.dataTypeDisplay || row.dataType }}</template>
            </el-table-column>
            <el-table-column label="描述" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ plainText(row.description) || "待补充" }}</template>
            </el-table-column>
            <el-table-column label="标签" min-width="140">
              <template #default="{ row }">{{ (row.tags || []).map((tag: any) => shortName(tag.tagFQN)).join("、") || "-" }}</template>
            </el-table-column>
          </el-table>
          <h3>质量检查（{{ selected.quality?.total || 0 }}）</h3>
          <el-table :data="selected.quality?.items || []" size="small">
            <el-table-column prop="name" label="检查项" min-width="180" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><el-tag :type="qualityColor(row.testCaseResult?.testCaseStatus)">{{ qualityLabel(row.testCaseResult?.testCaseStatus) }}</el-tag></template>
            </el-table-column>
          </el-table>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="viewLineage(selected)">查看血缘</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref } from "vue";
import { Refresh, Search } from "@element-plus/icons-vue";
import { ElCard, ElEmpty } from "element-plus";
import { useRouter } from "vue-router";
import { openmetadataApi } from "@/api";

const router = useRouter();
const loading = ref(false);
const assetLoading = ref(false);
const detailLoading = ref(false);
const omHealthy = ref(false);
const activeTab = ref("assets");
const query = ref("");
const entityType = ref("all");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const assets = ref<any[]>([]);
const summary = ref<any>({ counts: {}, coverage: {}, quality: { statuses: {} } });
const governance = ref<any>({ domains: [], dataProducts: [], glossaries: [], glossaryTerms: [], classifications: [] });
const quality = ref<any>({ items: [], total: 0 });
const detailVisible = ref(false);
const selected = ref<any>(null);

const entityTypes = [
  { label: "全部资产", value: "all" }, { label: "数据表", value: "table" },
  { label: "仪表盘", value: "dashboard" }, { label: "数据管道", value: "pipeline" },
  { label: "消息主题", value: "topic" }, { label: "机器学习模型", value: "mlmodel" },
  { label: "文件容器", value: "container" },
];

const summaryCards = computed(() => [
  { label: "资产总数", value: summary.value.totalAssets || 0, hint: "已纳入统一目录" },
  { label: "数据表", value: summary.value.counts?.table || 0, hint: "结构化数据资产" },
  { label: "责任人覆盖", value: `${summary.value.coverage?.owners || 0}%`, hint: "表资产治理覆盖" },
  { label: "描述覆盖", value: `${summary.value.coverage?.description || 0}%`, hint: "业务说明完整度" },
  { label: "标签覆盖", value: `${summary.value.coverage?.tags || 0}%`, hint: "分类与术语覆盖" },
  { label: "质量规则", value: summary.value.quality?.total || 0, hint: `${summary.value.quality?.statuses?.Failed || 0} 项失败` },
]);

const governanceList = defineComponent({
  name: "GovernanceList",
  props: { title: String, items: { type: Array, default: () => [] }, empty: String },
  setup(props) {
    return () => h(ElCard, { shadow: "never", class: "governance-list" }, {
      header: () => `${props.title}（${props.items.length}）`,
      default: () => props.items.length
        ? props.items.map((item: any) => h("div", { class: "governance-item" }, [
            h("b", item.displayName || item.name),
            h("small", plainText(item.description) || item.fullyQualifiedName || "暂无描述"),
          ]))
        : h(ElEmpty, { description: props.empty, imageSize: 54 }),
    });
  },
});

function plainText(value?: string) { return (value || "").replace(/<[^>]*>/g, "").replace(/[*_`#]/g, "").trim(); }
function shortName(value?: string) { return (value || "").split(".").pop() || ""; }
function ownerNames(items?: any[]) { return (items || []).map(item => item.displayName || item.name).filter(Boolean).join("、"); }
function typeLabel(type?: string) { return entityTypes.find(item => item.value === type)?.label || type || "未知"; }
function typeColor(type?: string): any { return ({ table: "primary", dashboard: "success", pipeline: "warning", topic: "info", mlmodel: "danger" } as any)[type || ""] || "info"; }
function qualityColor(status?: string): any { return status === "Success" ? "success" : status === "Failed" ? "danger" : "info"; }
function qualityLabel(status?: string) { return ({ Success: "通过", Failed: "失败", Aborted: "中止" } as any)[status || ""] || "未执行"; }
function entityFromLink(link?: string) { return (link || "").replace(/^<#E::table::/, "").replace(/>$/, "").replace(/::columns::/, "."); }
function formatTime(value?: number) { return value ? new Date(value).toLocaleString("zh-CN") : "-"; }
function statusCount(status: string) { return quality.value.items.filter((item: any) => item.testCaseResult?.testCaseStatus === status).length; }

async function loadAssets() {
  assetLoading.value = true;
  try {
    const result: any = await openmetadataApi.assets({ q: query.value || "*", entity_type: entityType.value, page: page.value, page_size: pageSize.value });
    assets.value = result?.items || [];
    total.value = result?.total || 0;
  } finally { assetLoading.value = false; }
}

function searchAssets() { page.value = 1; loadAssets(); }

async function loadAll() {
  loading.value = true;
  try {
    const health: any = await openmetadataApi.health();
    omHealthy.value = !!health?.healthy;
    if (!omHealthy.value) return;
    const [summaryResult, governanceResult, qualityResult] = await Promise.all([
      openmetadataApi.summary(), openmetadataApi.governance(), openmetadataApi.quality(),
    ]);
    summary.value = summaryResult || summary.value;
    governance.value = governanceResult || governance.value;
    quality.value = qualityResult || quality.value;
    await loadAssets();
  } catch { omHealthy.value = false; } finally { loading.value = false; }
}

function handleTabChange(name: string | number) {
  if (name === "assets" && !assets.value.length && omHealthy.value) loadAssets();
}

async function showDetail(row: any) {
  selected.value = { ...row };
  detailVisible.value = true;
  if (row.entityType !== "table") return;
  detailLoading.value = true;
  try { selected.value = await openmetadataApi.tableDetail(row.fullyQualifiedName); selected.value.entityType = "table"; }
  finally { detailLoading.value = false; }
}

function viewLineage(row: any) {
  if (!row) return;
  router.push({ path: "/assets/lineage", query: { fqn: row.fullyQualifiedName, type: row.entityType || "table" } });
}

function openMetadata() {
  window.open(`${window.location.protocol}//${window.location.hostname}:8585`, "_blank", "noopener,noreferrer");
}

onMounted(loadAll);
</script>

<style lang="scss" scoped>
.asset-center { padding: 4px; }
.hero { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hero h2 { margin: 0 0 6px; font-size: 24px; }
.hero p, .muted, .asset-fqn, .summary-hint { color: #909399; }
.hero p { margin: 0; }
.hero-actions { display: flex; align-items: center; gap: 10px; }
.summary-row { margin-top: 16px; }
.summary-card { margin-bottom: 16px; }
.summary-label { color: #606266; font-size: 13px; }
.summary-value { margin: 8px 0 4px; font-size: 27px; font-weight: 700; color: #303133; }
.summary-hint { font-size: 12px; }
.workspace { min-height: 520px; }
.toolbar { display: grid; grid-template-columns: minmax(280px, 1fr) 180px 90px; gap: 10px; margin-bottom: 16px; }
.asset-name { font-weight: 600; color: #303133; }
.asset-fqn { margin-top: 4px; font-size: 12px; word-break: break-all; }
.mini-tag { margin: 2px 4px 2px 0; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.governance-table { margin-top: 16px; }
.quality-head { display: flex; gap: 48px; padding: 14px 4px 22px; }
.quality-head div { display: flex; align-items: baseline; gap: 8px; color: #606266; }
.quality-head b { font-size: 28px; color: #303133; }
.quality-head .success b { color: #67c23a; }
.quality-head .danger b { color: #f56c6c; }
.drawer-title { font-size: 19px; font-weight: 600; color: #303133; }
.detail-tags { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0 22px; }
h3 { margin: 24px 0 12px; font-size: 16px; }
:deep(.governance-item) { padding: 11px 0; border-bottom: 1px solid #ebeef5; }
:deep(.governance-item:last-child) { border-bottom: 0; }
:deep(.governance-item b), :deep(.governance-item small) { display: block; }
:deep(.governance-item small) { margin-top: 5px; color: #909399; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
@media (max-width: 900px) { .hero { align-items: flex-start; gap: 14px; flex-direction: column; } .toolbar { grid-template-columns: 1fr; } }
</style>
