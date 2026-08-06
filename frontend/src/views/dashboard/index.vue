<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="card in statCards" :key="card.title">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon :size="32" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-title">{{ card.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 + 最近任务 -->
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
            <el-table-column prop="task_name" label="任务" width="120" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration_seconds" label="耗时" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 组件状态 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>组件连接状态</template>
          <el-row :gutter="16">
            <el-col :span="6" v-for="comp in components" :key="comp.code">
              <div class="component-status">
                <el-tag :type="comp.healthy ? 'success' : 'danger'" size="small">
                  {{ comp.healthy ? '正常' : '异常' }}
                </el-tag>
                <span class="comp-name">{{ comp.name }}</span>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef } from "vue";
import * as echarts from "echarts";
import { dashboardApi } from "@/api";

interface StatCard {
  title: string;
  value: number;
  icon: string;
  color: string;
}

interface ComponentItem {
  code: string;
  name: string;
  healthy: boolean;
}

const statCards = ref<StatCard[]>([
  { title: "数据源", value: 0, icon: "Coin", color: "#409eff" },
  { title: "DataX任务", value: 0, icon: "Sort", color: "#67c23a" },
  { title: "今日执行", value: 0, icon: "VideoPlay", color: "#e6a23c" },
  { title: "今日查询", value: 0, icon: "Monitor", color: "#f56c6c" },
]);

const recentTasks = ref<any[]>([]);
const components = ref<ComponentItem[]>([]);
const trendChartRef = ref<HTMLElement>();
const chartInstance = shallowRef<echarts.ECharts>();

onMounted(async () => {
  try {
    const [stats, tasks, compStatus] = await Promise.all([
      dashboardApi.stats(),
      dashboardApi.recentTasks(10),
      dashboardApi.componentStatus(),
    ]);

    statCards.value[0].value = stats.total_datasources || 0;
    statCards.value[1].value = stats.total_datax_tasks || 0;
    statCards.value[2].value = stats.today_executions || 0;
    statCards.value[3].value = stats.today_queries || 0;

    recentTasks.value = tasks || [];
    components.value = compStatus || [];

    // Render trend chart
    if (trendChartRef.value) {
      chartInstance.value = echarts.init(trendChartRef.value);
      chartInstance.value.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["成功", "失败"] },
        xAxis: { type: "category", data: stats.trend?.dates || [] },
        yAxis: { type: "value" },
        series: [
          { name: "成功", type: "bar", stack: "total", data: stats.trend?.success || [], itemStyle: { color: "#67c23a" } },
          { name: "失败", type: "bar", stack: "total", data: stats.trend?.failed || [], itemStyle: { color: "#f56c6c" } },
        ],
      });
    }
  } catch {
    // API not ready yet
  }
});

type TagType = "primary" | "success" | "warning" | "info" | "danger";

function statusType(status: string): TagType {
  const map: Record<string, TagType> = {
    success: "success",
    failed: "danger",
    running: "warning",
    queued: "info",
  };
  return map[status] || "info";
}
</script>

<style lang="scss" scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;

  .stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #303133;
  }

  .stat-title {
    font-size: 14px;
    color: #909399;
  }
}

.component-status {
  display: flex;
  align-items: center;
  gap: 8px;

  .comp-name {
    font-size: 14px;
  }
}
</style>
