<template>
  <div class="dashboard">
    <!-- Row 1: 4 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="card in statCards" :key="card.title">
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
            <el-table-column prop="task_type" label="类型" width="70">
              <template #default="{ row }">
                <el-tag size="small" :type="row.task_type === 'spark' ? 'warning' : 'info'">{{ row.task_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="dag_run_id" label="执行ID" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="mono-text">{{ row.dag_run_id?.substring(0, 16) }}...</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
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

    <!-- Row 3: 数据资产 + 指标 + 数据质量 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="8">
        <el-card shadow="hover" class="mini-stat-card">
          <template #header>数据资产统计</template>
          <div v-loading="omLoading">
            <template v-if="openmetadataHealthy">
              <div class="mini-stat-grid">
                <div class="mini-stat-item">
                  <div class="mini-stat-value">{{ omDbCount }}</div>
                  <div class="mini-stat-label">数据库</div>
                </div>
                <div class="mini-stat-item">
                  <div class="mini-stat-value">{{ omTableCount }}</div>
                  <div class="mini-stat-label">数据表</div>
                </div>
              </div>
            </template>
            <el-empty v-else description="OpenMetadata 未连接" :image-size="40" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="mini-stat-card">
          <template #header>指标服务调用</template>
          <div v-loading="cubeLoading">
            <template v-if="cubeHealthy">
              <div class="mini-stat-grid">
                <div class="mini-stat-item">
                  <div class="mini-stat-value">{{ cubeCount }}</div>
                  <div class="mini-stat-label">Cube 模型</div>
                </div>
                <div class="mini-stat-item">
                  <div class="mini-stat-value">{{ cubeMeasureCount }}</div>
                  <div class="mini-stat-label">度量数</div>
                </div>
              </div>
            </template>
            <el-empty v-else description="Cube 未连接" :image-size="40" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="mini-stat-card">
          <template #header>数据质量概览</template>
          <div v-loading="omLoading">
            <template v-if="openmetadataHealthy">
              <div class="quality-bars">
                <div class="quality-item">
                  <span class="quality-label">完整性</span>
                  <el-progress :percentage="95" :stroke-width="8" color="#22c55e" />
                </div>
                <div class="quality-item">
                  <span class="quality-label">准确性</span>
                  <el-progress :percentage="88" :stroke-width="8" color="#4366e5" />
                </div>
                <div class="quality-item">
                  <span class="quality-label">及时性</span>
                  <el-progress :percentage="92" :stroke-width="8" color="#f59e0b" />
                </div>
              </div>
            </template>
            <el-empty v-else description="OpenMetadata 未连接" :image-size="40" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Row 4: 组件状态 + 系统资源 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>组件连接状态</template>
          <el-row :gutter="16">
            <el-col :span="6" v-for="comp in components" :key="comp.code">
              <div class="component-card" :class="{ 'is-healthy': comp.healthy, 'is-unhealthy': !comp.healthy }">
                <div class="comp-status-dot"></div>
                <div class="comp-info">
                  <div class="comp-name">{{ comp.name }}</div>
                  <div class="comp-type">{{ comp.type }}</div>
                </div>
                <el-tag :type="comp.healthy ? 'success' : 'danger'" size="small" effect="light">
                  {{ comp.healthy ? '正常' : '异常' }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="24" v-if="components.length === 0">
              <el-empty description="暂无组件配置" :image-size="40" />
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>系统资源</template>
          <div class="resource-bars">
            <div class="resource-item">
              <div class="resource-header">
                <span>CPU 使用率</span>
                <span class="resource-value">32%</span>
              </div>
              <el-progress :percentage="32" :stroke-width="8" color="#4366e5" />
            </div>
            <div class="resource-item">
              <div class="resource-header">
                <span>内存使用率</span>
                <span class="resource-value">58%</span>
              </div>
              <el-progress :percentage="58" :stroke-width="8" color="#f59e0b" />
            </div>
            <div class="resource-item">
              <div class="resource-header">
                <span>磁盘使用率</span>
                <span class="resource-value">45%</span>
              </div>
              <el-progress :percentage="45" :stroke-width="8" color="#22c55e" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef } from "vue";
import * as echarts from "echarts";
import { dashboardApi, openmetadataApi, cubeApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

interface StatCard {
  title: string;
  value: number;
  icon: string;
  gradient: string;
}

interface ComponentItem {
  code: string;
  name: string;
  type: string;
  healthy: boolean;
}

const statCards = ref<StatCard[]>([
  { title: "数据源", value: 0, icon: "Coin", gradient: "linear-gradient(135deg, #4366e5, #6c8aff)" },
  { title: "数据任务", value: 0, icon: "Sort", gradient: "linear-gradient(135deg, #22c55e, #4ade80)" },
  { title: "今日执行", value: 0, icon: "VideoPlay", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)" },
  { title: "今日查询", value: 0, icon: "Monitor", gradient: "linear-gradient(135deg, #ef4444, #f87171)" },
]);

const recentTasks = ref<any[]>([]);
const components = ref<ComponentItem[]>([]);
const trendChartRef = ref<HTMLElement>();
const chartInstance = shallowRef<echarts.ECharts>();

const openmetadataHealthy = ref(false);
const cubeHealthy = ref(false);
const omLoading = ref(false);
const cubeLoading = ref(false);
const omDbCount = ref(0);
const omTableCount = ref(0);
const cubeCount = ref(0);
const cubeMeasureCount = ref(0);

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

    if (trendChartRef.value) {
      chartInstance.value = echarts.init(trendChartRef.value);
      chartInstance.value.setOption({
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
        legend: { data: ["成功", "失败"], bottom: 0, textStyle: { color: "#64748b" } },
        grid: { left: "3%", right: "4%", bottom: "12%", top: "8%", containLabel: true },
        xAxis: {
          type: "category",
          data: stats.trend?.dates || [],
          axisLine: { lineStyle: { color: "#e2e8f0" } },
          axisLabel: { color: "#94a3b8", fontSize: 12 },
        },
        yAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#f1f5f9" } },
          axisLabel: { color: "#94a3b8", fontSize: 12 },
        },
        series: [
          {
            name: "成功", type: "bar", stack: "total", barWidth: "40%",
            data: stats.trend?.success || [],
            itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#4ade80" }, { offset: 1, color: "#22c55e" }
            ]), borderRadius: [4, 4, 0, 0] },
          },
          {
            name: "失败", type: "bar", stack: "total", barWidth: "40%",
            data: stats.trend?.failed || [],
            itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#f87171" }, { offset: 1, color: "#ef4444" }
            ]), borderRadius: [4, 4, 0, 0] },
          },
        ],
      });
    }

    // Check OpenMetadata and Cube health
    omLoading.value = true;
    cubeLoading.value = true;
    
    Promise.all([
      openmetadataApi.health().catch(() => null),
      cubeApi.health().catch(() => null),
    ]).then(async ([omHealth, cubeHealth]) => {
      openmetadataHealthy.value = omHealth?.healthy || false;
      cubeHealthy.value = cubeHealth?.healthy || false;

      if (openmetadataHealthy.value) {
        try {
          const dbs = await openmetadataApi.databases();
          omDbCount.value = dbs?.length || 0;
          if (dbs?.length > 0) {
            const tables = await openmetadataApi.tables(dbs[0].fullyQualifiedName);
            omTableCount.value = tables?.length || 0;
          }
        } catch { /* ignore */ }
      }
      omLoading.value = false;

      if (cubeHealthy.value) {
        try {
          const meta = await cubeApi.meta();
          const cubes = meta?.cubes || {};
          cubeCount.value = Object.keys(cubes).length;
          cubeMeasureCount.value = Object.values(cubes).reduce((sum: number, c: any) => sum + (c.measures?.length || 0), 0);
        } catch { /* ignore */ }
      }
      cubeLoading.value = false;
    });

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

.mini-stat-grid {
  display: flex;
  gap: 24px;
  padding: 8px 0;
}

.mini-stat-item {
  flex: 1;

  .mini-stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #1e293b;
  }

  .mini-stat-label {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 2px;
  }
}

.quality-bars, .resource-bars {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

.quality-item {
  .quality-label {
    display: block;
    font-size: 13px;
    color: #64748b;
    margin-bottom: 6px;
  }
}

.resource-item {
  .resource-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;

    span {
      font-size: 13px;
      color: #64748b;
    }

    .resource-value {
      font-weight: 600;
      color: #1e293b;
    }
  }
}

.component-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  &.is-healthy {
    border-color: #dcfce7;
    background: #f0fdf4;
  }

  &.is-unhealthy {
    border-color: #fee2e2;
    background: #fef2f2;
  }

  .comp-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &.is-healthy .comp-status-dot {
    background: #22c55e;
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
  }

  &.is-unhealthy .comp-status-dot {
    background: #ef4444;
    box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
  }

  .comp-info {
    flex: 1;

    .comp-name {
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
    }

    .comp-type {
      font-size: 12px;
      color: #94a3b8;
    }
  }
}
</style>
