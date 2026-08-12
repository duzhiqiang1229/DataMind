<template>
  <div class="dashboard">
    <!-- Row 1: 5 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" class="stat-col" v-for="card in statCards" :key="card.title">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card-inner">
            <div class="stat-icon" :style="{ background: card.gradient }">
              <el-icon :size="22"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-title">{{ card.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Row 2: 趋势图 + 最近任务 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>最近 7 天同步趋势</template>
          <div ref="trendChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>最近任务</template>
          <el-table :data="recentTasks" size="small" :max-height="300">
            <el-table-column prop="dag_id" label="DAG 名称" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="mono-text">{{ row.dag_id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="dag_run_id" label="执行ID" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tooltip :content="row.dag_run_id || '-'" placement="top">
                  <span class="mono-text">{{ formatRunId(row.dag_run_id, row.start_date) }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.state)" size="small">{{ row.state }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration_seconds" label="耗时" width="60">
              <template #default="{ row }">
                {{ row.duration_seconds ? row.duration_seconds + 's' : '-' }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="recentTasks.length === 0" description="暂无任务" :image-size="40" />
        </el-card>
      </el-col>
    </el-row>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef } from "vue";
import * as echarts from "@/utils/echarts";
import { dashboardApi, openmetadataApi } from "@/api";
import { formatRunId } from "@/utils/format";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

interface StatCard {
  title: string;
  value: number | string;
  icon: string;
  gradient: string;
}

const statCards = ref<StatCard[]>([
  { title: "资产总数", value: 0, icon: "Collection", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  { title: "数据源", value: 0, icon: "Coin", gradient: "linear-gradient(135deg, #4366e5, #6c8aff)" },
  { title: "调度任务", value: "", icon: "Sort", gradient: "linear-gradient(135deg, #22c55e, #4ade80)" },
  { title: "指标数", value: 0, icon: "DataAnalysis", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)" },
  { title: "数据接口", value: 0, icon: "Share", gradient: "linear-gradient(135deg, #ef4444, #f87171)" },
]);

const recentTasks = ref<any[]>([]);
const trendChartRef = ref<HTMLElement>();
const chartInstance = shallowRef<echarts.ECharts>();

onMounted(async () => {
  openmetadataApi.summary()
    .then((summary: any) => { statCards.value[0].value = summary?.totalAssets || 0; })
    .catch(() => { statCards.value[0].value = 0; });

  try {
    const [stats, tasks] = await Promise.all([
      dashboardApi.stats(),
      dashboardApi.recentTasks(10),
    ]);

    statCards.value[1].value = stats.total_datasources || 0;
    statCards.value[2].value = `${stats.schedule_task_count || 0} / ${stats.today_executions || 0}`;
    statCards.value[3].value = stats.published_metrics_count || 0;
    statCards.value[4].value = stats.api_service_count || 0;

    recentTasks.value = tasks || [];

    if (trendChartRef.value) {
      const trendDates = stats.trend?.dates || [];
      const successData = stats.trend?.success || [];
      const failedData = stats.trend?.failed || [];
      const totalData = successData.map((v: number, i: number) => v + (failedData[i] || 0));
      chartInstance.value = echarts.init(trendChartRef.value);
      chartInstance.value.setOption({
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow", shadowStyle: { color: "rgba(99,102,241,0.05)" } },
          backgroundColor: "rgba(255,255,255,0.96)",
          borderColor: "#e2e8f0",
          borderWidth: 1,
          padding: [10, 14],
          textStyle: { color: "#334155", fontSize: 12 },
          formatter: (params: any) => {
            const list = Array.isArray(params) ? params : [params];
            const idx = list[0]?.dataIndex ?? 0;
            const date = trendDates[idx] || "";
            const success = successData[idx] ?? 0;
            const failed = failedData[idx] ?? 0;
            const dot = (c: string) => `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${c};"></span>`;
            return [
              `<div style="font-weight:600;margin-bottom:6px;">${date}</div>`,
              `<div style="display:flex;align-items:center;gap:6px;">${dot("#22c55e")}成功：<b>${success}</b></div>`,
              `<div style="display:flex;align-items:center;gap:6px;">${dot("#ef4444")}失败：<b>${failed}</b></div>`,
              `<div style="margin-top:4px;color:#64748b;">合计：<b style="color:#334155;">${success + failed}</b></div>`,
            ].join("");
          },
        },
        legend: {
          top: 0,
          right: 4,
          itemWidth: 10,
          itemHeight: 10,
          icon: "roundRect",
          textStyle: { color: "#64748b", fontSize: 12 },
          data: ["成功", "失败"],
        },
        grid: { left: 8, right: 8, top: 42, bottom: 4, containLabel: true },
        xAxis: {
          type: "category",
          data: trendDates,
          axisLine: { lineStyle: { color: "#e2e8f0" } },
          axisTick: { show: false },
          axisLabel: { color: "#94a3b8", fontSize: 12, margin: 12 },
        },
        yAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#f1f5f9", type: "dashed" } },
          axisLabel: { color: "#94a3b8", fontSize: 12 },
        },
        series: [
          {
            name: "成功", type: "bar", barWidth: 18,
            data: successData,
            itemStyle: {
              borderRadius: [4, 4, 0, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "#4ade80" }, { offset: 1, color: "#16a34a" },
              ]),
              shadowColor: "rgba(34,197,94,0.25)",
              shadowBlur: 6,
              shadowOffsetY: 2,
            },
            emphasis: { itemStyle: { opacity: 0.85 } },
          },
          {
            name: "失败", type: "bar", barWidth: 18,
            data: failedData,
            itemStyle: {
              borderRadius: [4, 4, 0, 0],
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "#fca5a5" }, { offset: 1, color: "#dc2626" },
              ]),
              shadowColor: "rgba(239,68,68,0.2)",
              shadowBlur: 6,
              shadowOffsetY: 2,
            },
            emphasis: { itemStyle: { opacity: 0.85 } },
          },
          {
            name: "合计", type: "line", smooth: true, symbol: "circle", symbolSize: 5,
            data: totalData,
            lineStyle: { width: 2, color: "#4366e5" },
            itemStyle: { color: "#4366e5" },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "rgba(67,102,229,0.18)" },
                { offset: 1, color: "rgba(67,102,229,0)" },
              ]),
            },
            z: 5,
          },
        ],
      });
    }

  } catch {
    // API not ready yet
  }
});

function statusType(status: string): TagType {
  const map: Record<string, TagType> = { success: "success", failed: "danger", running: "warning", queued: "info" };
  return map[status] || "info";
}
</script>

<style lang="scss" scoped>
.stat-col {
  flex: 0 0 20%;
  max-width: 20%;
}

.stat-card {
  :deep(.el-card__body) {
    padding: 20px;
  }
}

.stat-card-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.stat-info {
  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.2;
  }

  .stat-title {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 2px;
  }
}

.mono-text {
  font-family: "Courier New", monospace;
  font-size: 12px;
  color: #64748b;
}
</style>
