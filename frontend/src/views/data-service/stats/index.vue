<template>
  <div class="data-service-stats">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>调用监控</span>
          <div class="header-actions">
            <el-select v-model="statsDays" size="small" style="width: 140px" @change="loadStats">
              <el-option label="近 7 天" :value="7" />
              <el-option label="近 14 天" :value="14" />
              <el-option label="近 30 天" :value="30" />
            </el-select>
            <el-button type="primary" :icon="Refresh" @click="loadAll">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- Row 1: stat cards -->
      <el-row :gutter="16" class="stat-row">
        <el-col :span="6">
          <div class="stat-card total">
            <div class="stat-label">总调用次数</div>
            <div class="stat-value">{{ stats.total_calls ?? 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card success">
            <div class="stat-label">成功次数</div>
            <div class="stat-value">{{ stats.success ?? 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card failed">
            <div class="stat-label">失败次数</div>
            <div class="stat-value">{{ stats.failed ?? 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card avg">
            <div class="stat-label">平均耗时(ms)</div>
            <div class="stat-value">{{ formatAverageElapsed(stats.avg_elapsed_ms) }}</div>
          </div>
        </el-col>
      </el-row>

      <!-- Row 2: trend chart -->
      <div class="chart-wrapper" v-loading="chartLoading">
        <div ref="chartRef" class="trend-chart"></div>
      </div>

      <!-- Row 3: recent logs -->
      <div class="logs-section">
        <div class="section-title">
          <span>最近调用记录</span>
          <el-select
            v-model="selectedApiId"
            placeholder="全部服务"
            clearable
            filterable
            size="small"
            style="width: 280px"
            @change="loadLogs"
          >
            <el-option v-for="api in apiOptions" :key="api.id" :label="api.path || api.name" :value="api.id" />
          </el-select>
        </div>
        <el-table v-loading="logsLoading" :data="logList" border stripe>
          <el-table-column prop="api_path" label="API 路径" min-width="200" show-overflow-tooltip />
          <el-table-column prop="caller_username" label="调用者" min-width="120" show-overflow-tooltip />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)" size="small">{{ formatStatus(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="row_count" label="行数" width="100" align="right" />
          <el-table-column prop="elapsed_ms" label="耗时(ms)" width="110" align="right" />
          <el-table-column label="调用时间" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination
            v-model:current-page="logPage"
            v-model:page-size="logPageSize"
            :total="logTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadLogs"
            @current-change="loadLogs"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount, nextTick } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { formatDateTime } from "@/utils/format";
import * as echarts from "@/utils/echarts";
import { dataServiceApi, dataServiceLogApi } from "@/api";

type TagType = "primary" | "success" | "info" | "warning" | "danger";

interface ApiOption {
  id: string;
  name?: string;
  path?: string;
}

interface LogRow {
  api_path: string;
  caller_username: string;
  status: string;
  row_count: number;
  elapsed_ms: number;
  created_at: string;
}

const statsDays = ref(7);
const stats = ref<{ total_calls?: number; success?: number; failed?: number; avg_elapsed_ms?: number; daily?: any[] }>({});

const chartLoading = ref(false);
const chartRef = ref<HTMLElement | null>(null);
const chartInstance = shallowRef<echarts.ECharts | null>(null);

const apiOptions = ref<ApiOption[]>([]);
const selectedApiId = ref("");
const logList = ref<LogRow[]>([]);
const logPage = ref(1);
const logPageSize = ref(20);
const logTotal = ref(0);
const logsLoading = ref(false);

const getStatusTagType = (status: string): TagType => {
  const s = (status || "").toLowerCase();
  if (s === "success" || s === "200" || s === "ok") return "success";
  if (s === "failed" || s === "error" || s === "500") return "danger";
  return "warning";
};

const formatStatus = (status: string): string => {
  const s = (status || "").toLowerCase();
  if (s === "success" || s === "200" || s === "ok") return "成功";
  if (s === "failed" || s === "error" || s === "500") return "失败";
  return status || "—";
};

const formatAverageElapsed = (value?: number): string => {
  const milliseconds = Number(value ?? 0);
  if (!Number.isFinite(milliseconds)) return "0";
  return Math.round(milliseconds).toLocaleString("zh-CN");
};

const loadStats = async () => {
  chartLoading.value = true;
  try {
    const res = await dataServiceLogApi.callStats(statsDays.value);
    const data = (res as any)?.data ?? res;
    stats.value = {
      total_calls: data?.total_calls ?? data?.total ?? 0,
      success: data?.success ?? data?.success_count ?? 0,
      failed: data?.failed ?? data?.failed_count ?? 0,
      avg_elapsed_ms: data?.avg_elapsed_ms ?? data?.avg_elapsed ?? 0,
      daily: data?.daily ?? data?.daily_trend ?? data?.trend ?? [],
    };
    renderChart();
  } catch {
    ElMessage.error("加载调用统计失败");
  } finally {
    chartLoading.value = false;
  }
};

const renderChart = async () => {
  await nextTick();
  if (!chartRef.value) return;
  if (!chartInstance.value) {
    chartInstance.value = echarts.init(chartRef.value);
  }
  const daily = stats.value.daily ?? [];
  const dates = daily.map((d: any) => d.date ?? d.day ?? "");
  const successData = daily.map((d: any) => d.success ?? d.success_count ?? 0);
  const failedData = daily.map((d: any) => d.failed ?? d.failed_count ?? 0);

  const option: echarts.EChartsOption = {
    title: { text: "每日调用趋势", left: "center", textStyle: { fontSize: 14 } },
    tooltip: { trigger: "axis" },
    legend: { data: ["成功", "失败"], bottom: 0 },
    grid: { left: 48, right: 24, top: 48, bottom: 48 },
    xAxis: { type: "category", data: dates, boundaryGap: false },
    yAxis: { type: "value", minInterval: 1 },
    series: [
      {
        name: "成功",
        type: "line",
        smooth: true,
        data: successData,
        itemStyle: { color: "#67c23a" },
        areaStyle: { opacity: 0.15 },
      },
      {
        name: "失败",
        type: "line",
        smooth: true,
        data: failedData,
        itemStyle: { color: "#f56c6c" },
        areaStyle: { opacity: 0.15 },
      },
    ],
  };
  chartInstance.value.setOption(option, true);
};

const loadApiOptions = async () => {
  try {
    const result: any = await dataServiceApi.list({ page: 1, page_size: 100 });
    apiOptions.value = (result?.items || []).map((item: any) => ({
      id: item.id,
      name: item.api_name,
      path: `${item.api_name} · ${item.api_path}`,
    }));
  } catch {
    apiOptions.value = [];
  }
};

const loadLogs = async () => {
  logsLoading.value = true;
  try {
    const params = {
      page: logPage.value,
      page_size: logPageSize.value,
    };
    const res = selectedApiId.value
      ? await dataServiceLogApi.logs(selectedApiId.value, params)
      : await dataServiceLogApi.allLogs(params);
    const data = (res as any)?.data ?? res;
    logList.value = data?.items ?? (Array.isArray(data) ? data : []);
    logTotal.value = data?.total ?? logList.value.length;
  } catch {
    ElMessage.error("加载调用日志失败");
    logList.value = [];
  } finally {
    logsLoading.value = false;
  }
};

const loadAll = () => {
  loadStats();
  loadApiOptions();
  loadLogs();
};

const handleResize = () => {
  chartInstance.value?.resize();
};

onMounted(() => {
  loadStats();
  loadApiOptions();
  loadLogs();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance.value?.dispose();
  chartInstance.value = null;
});
</script>

<style lang="scss" scoped>
.data-service-stats {
  padding: 16px;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .stat-row {
    margin-bottom: 16px;
  }

  .stat-card {
    border-radius: 6px;
    padding: 20px;
    color: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

    &.total { background: linear-gradient(135deg, #409eff, #337ecc); }
    &.success { background: linear-gradient(135deg, #67c23a, #529b2e); }
    &.failed { background: linear-gradient(135deg, #f56c6c, #c45656); }
    &.avg { background: linear-gradient(135deg, #e6a23c, #b88230); }
  }

  .stat-label {
    font-size: 13px;
    opacity: 0.9;
  }

  .stat-value {
    font-size: 28px;
    font-weight: 600;
    margin-top: 8px;
  }

  .chart-wrapper {
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 16px;
  }

  .trend-chart {
    width: 100%;
    height: 320px;
  }

  .logs-section {
    margin-top: 8px;
  }

  .section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    font-weight: 600;
    color: #303133;
  }

  .pagination {
    margin-top: 12px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
