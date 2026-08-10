<template>
  <div class="metrics-query">
    <el-alert
      v-if="!cubeHealthy && !loadingMeta"
      type="warning"
      :closable="false"
      style="margin-bottom: 12px;"
    >
      Cube 组件未连接，请先在「系统管理 → 组件配置」中配置并启动 Cube。
    </el-alert>

    <div class="workbench">
      <!-- 左侧：指标列表 -->
      <div class="panel metric-list-panel">
        <div class="panel-header">
          <span class="panel-title">指标</span>
          <el-button type="primary" size="small" :icon="Plus" @click="goCreate">新建</el-button>
        </div>
        <el-input
          v-model="browseKeyword"
          placeholder="搜索指标"
          :prefix-icon="Search"
          clearable
          size="small"
          class="browse-search"
          @input="loadBrowseMetrics"
        />
        <el-scrollbar class="metric-list">
          <div
            v-for="m in browseMetrics"
            :key="m.id"
            class="metric-item"
            :class="{ active: selectedMetric?.id === m.id }"
            @click="selectMetric(m)"
          >
            <div class="metric-name">{{ m.metric_name }}</div>
            <div class="metric-sub">
              {{ m.cube_name }} · {{ (m.cube_measure || '').split('.').pop() }}
            </div>
          </div>
          <el-empty v-if="!browseLoading && browseMetrics.length === 0" description="暂无指标" :image-size="48" />
        </el-scrollbar>
      </div>

      <!-- 右侧：查询配置 + 结果 -->
      <div class="panel query-panel">
        <div class="query-config">
          <div class="config-row">
            <el-select v-model="queryCubeName" placeholder="选择 Cube" filterable size="small" style="width: 200px;" @change="onCubeChange">
              <el-option v-for="c in cubes" :key="c.name" :label="c.title || c.name" :value="c.name" />
            </el-select>
            <el-select v-model="query.measures" multiple filterable placeholder="度量（必选）" size="small" style="flex: 1; min-width: 220px;">
              <el-option v-for="m in cubeMeasures" :key="m.name" :label="m.title || m.name" :value="m.name" />
            </el-select>
            <el-select v-model="query.dimensions" multiple filterable placeholder="维度" size="small" style="flex: 1; min-width: 220px;">
              <el-option v-for="d in cubeDimensions" :key="d.name" :label="d.title || d.name" :value="d.name" />
            </el-select>
          </div>

          <div class="config-row">
            <el-select v-model="query.timeDimension" placeholder="时间维度" clearable size="small" style="width: 200px;">
              <el-option v-for="d in cubeTimeDimensions" :key="d.name" :label="d.title || d.name" :value="d.name" />
            </el-select>
            <el-date-picker
              v-model="query.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              size="small"
              style="width: 260px;"
              :disabled="!query.timeDimension"
            />
            <el-select v-model="query.granularity" placeholder="粒度" size="small" style="width: 110px;" :disabled="!query.timeDimension">
              <el-option label="按日" value="day" />
              <el-option label="按周" value="week" />
              <el-option label="按月" value="month" />
              <el-option label="按季" value="quarter" />
              <el-option label="按年" value="year" />
            </el-select>
            <el-input-number v-model="query.limit" :min="1" :max="10000" :step="100" size="small" style="width: 120px;" />
            <span class="config-label">条数</span>
          </div>

          <div class="config-row filters-row">
            <div class="filters">
              <div v-for="(f, i) in query.filters" :key="i" class="filter-line">
                <el-select v-model="f.member" placeholder="过滤维度" filterable size="small" style="width: 180px;">
                  <el-option v-for="d in cubeDimensions" :key="d.name" :label="d.title || d.name" :value="d.name" />
                </el-select>
                <el-select v-model="f.operator" size="small" style="width: 120px;">
                  <el-option label="等于" value="equals" />
                  <el-option label="不等于" value="notEquals" />
                  <el-option label="包含" value="contains" />
                  <el-option label="不包含" value="notContains" />
                  <el-option label="大于" value="gt" />
                  <el-option label="大于等于" value="gte" />
                  <el-option label="小于" value="lt" />
                  <el-option label="小于等于" value="lte" />
                </el-select>
                <el-input v-model="f.values[0]" placeholder="过滤值" size="small" style="width: 160px;" />
                <el-button link type="danger" :icon="Delete" @click="removeFilter(i)" />
              </div>
            </div>
            <el-button link type="primary" :icon="Plus" @click="addFilter">添加过滤</el-button>
          </div>

          <div class="config-row actions-row">
            <el-button type="primary" :icon="VideoPlay" :loading="querying" @click="executeQuery">查询</el-button>
            <el-button :icon="RefreshLeft" @click="resetQuery">重置</el-button>
            <el-button :icon="Refresh" size="small" @click="loadMeta" :loading="loadingMeta" style="margin-left: auto;">刷新元数据</el-button>
          </div>
        </div>

        <!-- 结果 -->
        <div v-if="queryResult" class="query-result">
          <div class="result-header">
            <div class="result-tabs">
              <span :class="{ active: resultView === 'table' }" @click="resultView = 'table'">表格</span>
              <span :class="{ active: resultView === 'chart' }" @click="resultView = 'chart'">图表</span>
            </div>
            <span class="result-info">
              返回 {{ queryResult.data?.length || 0 }} 行
              <template v-if="queryResult.lastRefreshTime">· 缓存 {{ formatTime(queryResult.lastRefreshTime) }}</template>
            </span>
          </div>

          <el-table v-show="resultView === 'table'" :data="queryResult.data || []" border size="small" :max-height="420">
            <el-table-column
              v-for="col in resultColumns"
              :key="col"
              :prop="col"
              :label="columnLabel(col)"
              min-width="130"
              show-overflow-tooltip
            />
          </el-table>

          <div v-show="resultView === 'chart'" ref="chartRef" class="chart-box"></div>
        </div>
        <div v-else class="result-placeholder">
          <el-icon><DataAnalysis /></el-icon>
          <span>从左侧选择指标，或配置度量后点击「查询」</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Plus, Search, RefreshLeft, Refresh, VideoPlay, Delete, DataAnalysis } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import * as echarts from "echarts";
import { cubeApi, metricDefinitionApi } from "@/api";

const router = useRouter();
const route = useRoute();

const loadingMeta = ref(false);
const cubeHealthy = ref(false);
const metaData = ref<any>(null);

const cubes = computed(() => (metaData.value?.cubes || []) as any[]);
const cubeMeasures = computed(() => {
  const c = cubes.value.find((x: any) => x.name === queryCubeName.value);
  return (c?.measures || []) as any[];
});
const cubeDimensions = computed(() => {
  const c = cubes.value.find((x: any) => x.name === queryCubeName.value);
  return (c?.dimensions || []) as any[];
});
const cubeTimeDimensions = computed(() =>
  cubeDimensions.value.filter((d: any) => d.type === "time"),
);

async function loadMeta() {
  loadingMeta.value = true;
  try {
    const [health, meta] = await Promise.all([
      cubeApi.health(),
      cubeApi.meta().catch(() => null),
    ]);
    cubeHealthy.value = health?.healthy || false;
    if (meta) metaData.value = meta;
  } catch {
    // handled
  } finally {
    loadingMeta.value = false;
  }
}

// 指标列表
const browseLoading = ref(false);
const browseMetrics = ref<any[]>([]);
const browseKeyword = ref("");
const selectedMetric = ref<any>(null);
const queryCubeName = ref("");

async function loadBrowseMetrics() {
  browseLoading.value = true;
  try {
    const res = await metricDefinitionApi.list({
      page: 1,
      page_size: 100,
      keyword: browseKeyword.value || undefined,
    });
    browseMetrics.value = res.items || [];
  } catch {
    // handled
  } finally {
    browseLoading.value = false;
  }
}

// 查询配置
const querying = ref(false);
const queryResult = ref<any>(null);
const resultView = ref("table");

const query = reactive({
  measures: [] as string[],
  dimensions: [] as string[],
  timeDimension: "",
  dateRange: [] as string[],
  granularity: "day",
  filters: [] as { member: string; operator: string; values: string[] }[],
  limit: 1000,
});

function selectMetric(m: any) {
  selectedMetric.value = m;
  queryCubeName.value = m.cube_name || "";
  query.measures = m.cube_measure ? [m.cube_measure] : [];
  query.dimensions = [...(m.dimensions || [])];
  query.timeDimension = m.default_time_dimension || "";
  query.dateRange = [];
  query.filters = [];
  queryResult.value = null;
  executeQuery();
}

function onCubeChange() {
  query.measures = [];
  query.dimensions = [];
  query.timeDimension = "";
  query.dateRange = [];
  query.filters = [];
  queryResult.value = null;
}

function addFilter() {
  query.filters.push({ member: "", operator: "equals", values: [""] });
}

function removeFilter(index: number) {
  query.filters.splice(index, 1);
}

function resetQuery() {
  query.measures = selectedMetric.value?.cube_measure ? [selectedMetric.value.cube_measure] : [];
  query.dimensions = [...(selectedMetric.value?.dimensions || [])];
  query.timeDimension = "";
  query.dateRange = [];
  query.granularity = "day";
  query.filters = [];
  query.limit = 1000;
  queryResult.value = null;
}

async function executeQuery() {
  if (query.measures.length === 0) {
    ElMessage.warning("请选择至少一个度量");
    return;
  }
  const cubeQuery: any = {
    measures: query.measures,
    dimensions: query.dimensions,
    limit: query.limit,
  };
  const filters = query.filters.filter((f) => f.member && f.values[0] !== "");
  if (filters.length) {
    cubeQuery.filters = filters.map((f) => ({
      member: f.member,
      operator: f.operator,
      values: [f.values[0]],
    }));
  }
  if (query.timeDimension) {
    const td: any = { dimension: query.timeDimension, granularity: query.granularity };
    if (query.dateRange.length === 2) {
      td.dateRange = query.dateRange;
    }
    cubeQuery.timeDimensions = [td];
  }
  querying.value = true;
  try {
    queryResult.value = await cubeApi.load(cubeQuery);
    resultView.value = query.timeDimension ? "chart" : "table";
    ElMessage.success("查询成功");
  } catch {
    // handled
  } finally {
    querying.value = false;
  }
}

function goCreate() {
  router.push({ path: "/metrics/definitions", query: { create: "1" } });
}

// 结果展示
const resultColumns = computed(() => {
  const rows = queryResult.value?.data || [];
  return rows[0] ? Object.keys(rows[0]) : [];
});

function columnLabel(key: string): string {
  const ann = queryResult.value?.annotation || {};
  return (
    ann.measures?.[key]?.shortTitle ||
    ann.dimensions?.[key]?.shortTitle ||
    String(key).split(".").pop() ||
    key
  );
}

function formatTime(iso: string): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const utc8 = new Date(d.getTime() + 8 * 3600 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${utc8.getUTCFullYear()}-${pad(utc8.getUTCMonth() + 1)}-${pad(utc8.getUTCDate())} ${pad(utc8.getUTCHours())}:${pad(utc8.getUTCMinutes())}`;
}

// 图表
const chartRef = ref<HTMLElement>();
let chartInstance: any = null;

function fmtX(key: string, value: any, isTime: boolean): string {
  if (value === null || value === undefined) return "(空)";
  if (isTime) return String(value).slice(0, 10);
  return String(value);
}

function renderChart() {
  nextTick(() => {
    if (!chartRef.value || !queryResult.value) return;
    if (!chartInstance) {
      chartInstance = echarts.init(chartRef.value);
    }
    const rows = queryResult.value.data || [];
    const measures = query.measures;
    const isTime = !!query.timeDimension;
    const xKey = query.timeDimension || query.dimensions[0] || "";
    const xData = rows.map((r: any) => fmtX(xKey, r[xKey], isTime));
    const series = measures.map((m: string) => ({
      name: columnLabel(m),
      type: isTime ? "line" : "bar",
      smooth: isTime,
      barMaxWidth: 36,
      data: rows.map((r: any) => {
        const v = parseFloat(r[m]);
        return Number.isNaN(v) ? null : v;
      }),
    }));
    chartInstance.setOption(
      {
        tooltip: { trigger: "axis" },
        legend: { data: measures.map(columnLabel), bottom: 0 },
        grid: { left: "3%", right: "4%", bottom: "12%", top: "8%", containLabel: true },
        xAxis: {
          type: "category",
          data: xData,
          axisLabel: { rotate: xData.length > 8 ? 30 : 0 },
        },
        yAxis: { type: "value" },
        series,
      },
      true,
    );
  });
}

watch(resultView, (v) => {
  if (v === "chart") renderChart();
});
watch(queryResult, () => {
  if (resultView.value === "chart") renderChart();
});

onMounted(async () => {
  await Promise.all([loadBrowseMetrics(), loadMeta()]);
  const metricId = route.query.metric_id;
  if (metricId) {
    const m = browseMetrics.value.find((x) => x.id === metricId);
    if (m) selectMetric(m);
  }
});

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<style lang="scss" scoped>
.workbench {
  display: flex;
  gap: 12px;
  height: calc(100vh - 160px);
  min-height: 480px;
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

.metric-list-panel {
  width: 240px;
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  .panel-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.browse-search {
  padding: 10px 12px 4px;
}

.metric-list {
  flex: 1;
  padding: 6px 8px 10px;
}

.metric-item {
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

  .metric-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .metric-sub {
    margin-top: 2px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.query-panel {
  flex: 1;
  min-width: 0;
}

.query-config {
  padding: 12px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  .config-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }

    .config-label {
      font-size: 13px;
      color: var(--el-text-color-secondary);
      white-space: nowrap;
    }
  }

  .filters-row {
    align-items: flex-start;
  }

  .filters {
    flex: 1;
    min-width: 0;
  }

  .filter-line {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
  }

  .actions-row {
    margin-top: 4px;
  }
}

.query-result {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px 6px;

    .result-tabs {
      display: flex;
      gap: 4px;

      span {
        padding: 4px 14px;
        border-radius: 6px;
        font-size: 13px;
        color: var(--el-text-color-secondary);
        cursor: pointer;
        border: 1px solid transparent;

        &.active {
          color: var(--el-color-primary);
          background: var(--el-color-primary-light-9);
          border-color: var(--el-color-primary-light-5);
          font-weight: 500;
        }
      }
    }

    .result-info {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }

  .chart-box {
    flex: 1;
    min-height: 340px;
    padding: 0 8px 8px;
  }
}

.result-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;

  .el-icon {
    font-size: 36px;
    color: var(--el-border-color);
  }
}
</style>
