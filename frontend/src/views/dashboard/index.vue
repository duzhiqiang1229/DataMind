<template>
  <div class="dashboard">
    <!-- Row 1: 4 统计卡片 -->
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

    <!-- Row 2: 趋势图 (span=16) + 最近任务 (span=8) -->
    <el-row :gutter="16" class="section-row">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>数据同步状态趋势</template>
          <div ref="trendChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>最近任务</template>
          <el-table :data="recentTasks" size="small" :max-height="300">
            <el-table-column prop="task_type" label="类型" width="80" />
            <el-table-column prop="dag_run_id" label="运行ID" width="100" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration_seconds" label="耗时(秒)" width="80" />
            <el-table-column prop="rows_read" label="读取行数" width="90" />
            <el-table-column prop="rows_written" label="写入行数" width="90" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- Row 3: 数据资产统计 (span=8) + 指标服务调用 (span=8) + 数据质量概览 (span=8) -->
    <el-row :gutter="16" class="section-row">
      <el-col :span="8">
        <el-card shadow="hover" class="asset-card">
          <template #header>数据资产统计</template>
          <div v-if="assetLoading" class="card-loading">
            <el-skeleton :rows="4" animated />
          </div>
          <el-empty v-else-if="!openmetadataHealthy" description="组件未连接" :image-size="60" />
          <div v-else class="asset-stats">
            <div class="stat-line">
              <span class="stat-label">数据库</span>
              <span class="stat-num">{{ assetStats.databases }}</span>
            </div>
            <div class="stat-line">
              <span class="stat-label">数据表</span>
              <span class="stat-num">{{ assetStats.tables }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="asset-card">
          <template #header>指标服务调用统计</template>
          <div v-if="cubeLoading" class="card-loading">
            <el-skeleton :rows="4" animated />
          </div>
          <el-empty v-else-if="!cubeHealthy" description="组件未连接" :image-size="60" />
          <div v-else class="asset-stats">
            <div class="stat-line">
              <span class="stat-label">Cube 数</span>
              <span class="stat-num">{{ cubeStats.cubes }}</span>
            </div>
            <div class="stat-line">
              <span class="stat-label">指标数</span>
              <span class="stat-num">{{ cubeStats.measures }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="asset-card">
          <template #header>数据质量概览</template>
          <div v-if="qualityLoading" class="card-loading">
            <el-skeleton :rows="4" animated />
          </div>
          <el-empty v-else-if="!openmetadataHealthy" description="组件未连接" :image-size="60" />
          <div v-else class="asset-stats">
            <div class="stat-line">
              <span class="stat-label">测试套件</span>
              <span class="stat-num">{{ qualityStats.suites }}</span>
            </div>
            <div class="stat-line">
              <span class="stat-label">测试用例</span>
              <span class="stat-num">{{ qualityStats.tests }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Row 4: 组件连接状态 (span=16) + 系统资源监控 (span=8) -->
    <el-row :gutter="16" class="section-row">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>组件连接状态</template>
          <el-row :gutter="16">
            <el-col :span="6" v-for="comp in components" :key="comp.code">
              <div class="component-status">
                <el-tag :type="comp.healthy ? 'success' : 'danger'" size="small">
                  {{ comp.healthy ? '正常' : '异常' }}
                </el-tag>
                <span class="comp-name">{{ comp.name }}</span>
                <span class="comp-type">{{ comp.type }}</span>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>系统资源监控</template>
          <div class="resource-monitor">
            <div class="resource-line">
              <span class="resource-label">CPU 使用率</span>
              <el-progress :percentage="systemStats.cpu" :color="progressColor(systemStats.cpu)" :stroke-width="14" />
            </div>
            <div class="resource-line">
              <span class="resource-label">内存使用率</span>
              <el-progress :percentage="systemStats.memory" :color="progressColor(systemStats.memory)" :stroke-width="14" />
            </div>
            <div class="resource-line">
              <span class="resource-label">磁盘使用率</span>
              <el-progress :percentage="systemStats.disk" :color="progressColor(systemStats.disk)" :stroke-width="14" />
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
  color: string;
}

interface ComponentItem {
  code: string;
  name: string;
  type: string;
  base_url: string;
  healthy: boolean;
  last_check_at: string;
}

// Row 1: 统计卡片
const statCards = ref<StatCard[]>([
  { title: "数据源", value: 0, icon: "Coin", color: "#409eff" },
  { title: "数据任务", value: 0, icon: "Sort", color: "#67c23a" },
  { title: "今日执行", value: 0, icon: "VideoPlay", color: "#e6a23c" },
  { title: "今日查询", value: 0, icon: "Monitor", color: "#f56c6c" },
]);

// Row 2: 趋势图 + 最近任务
const recentTasks = ref<any[]>([]);
const trendChartRef = ref<HTMLElement>();
const chartInstance = shallowRef<echarts.ECharts>();

// Row 3: 数据资产 / 指标服务 / 数据质量
const openmetadataHealthy = ref(false);
const cubeHealthy = ref(false);
const assetLoading = ref(true);
const cubeLoading = ref(true);
const qualityLoading = ref(true);

const assetStats = ref({ databases: 0, tables: 0 });
const cubeStats = ref({ cubes: 0, measures: 0 });
const qualityStats = ref({ suites: 0, tests: 0 });

// Row 4: 组件状态 + 系统资源
const components = ref<ComponentItem[]>([]);
const systemStats = ref({ cpu: 0, memory: 0, disk: 0 });

onMounted(async () => {
  // 加载 dashboard 核心 API
  loadDashboardData();

  // 并行加载 OpenMetadata / Cube 连接及统计
  loadOpenmetadataData();
  loadCubeData();

  // 系统资源占位（本地服务器未提供 API，使用占位数据）
  loadSystemStats();
});

async function loadDashboardData() {
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
    components.value = (compStatus || []) as ComponentItem[];

    // 渲染趋势图
    renderTrendChart(stats.trend);
  } catch {
    // API 未就绪
  }
}

function renderTrendChart(trend: any) {
  if (!trendChartRef.value) return;
  chartInstance.value = echarts.init(trendChartRef.value);
  chartInstance.value.setOption({
    tooltip: { trigger: "axis" },
    legend: { data: ["成功", "失败"] },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: { type: "category", data: trend?.dates || [] },
    yAxis: { type: "value" },
    series: [
      { name: "成功", type: "bar", stack: "total", data: trend?.success || [], itemStyle: { color: "#67c23a" } },
      { name: "失败", type: "bar", stack: "total", data: trend?.failed || [], itemStyle: { color: "#f56c6c" } },
    ],
  });
}

async function loadOpenmetadataData() {
  // 数据资产统计 和 数据质量概览 都依赖 OpenMetadata
  try {
    const health = await openmetadataApi.health();
    openmetadataHealthy.value = health?.healthy === true;
  } catch {
    openmetadataHealthy.value = false;
  }

  if (!openmetadataHealthy.value) {
    assetLoading.value = false;
    qualityLoading.value = false;
    return;
  }

  // 加载数据库列表
  try {
    const databases = await openmetadataApi.databases();
    const dbList = Array.isArray(databases) ? databases : (databases as any)?.data || [];
    assetStats.value.databases = dbList.length;

    // 统计表数量（逐库获取，限制总数以避免过多请求）
    let tableCount = 0;
    for (const db of dbList.slice(0, 5)) {
      try {
        const fqn = db.fullyQualifiedName || db.name;
        const tables = await openmetadataApi.tables(fqn);
        tableCount += Array.isArray(tables) ? tables.length : (tables as any)?.paging?.total || 0;
      } catch {
        // 单库获取失败跳过
      }
    }
    assetStats.value.tables = tableCount;
  } catch {
    // 获取资产数据失败，保持为 0
  }
  assetLoading.value = false;

  // 数据质量概览（OpenMetadata 暂未提供专门的质量接口，使用占位统计）
  // 如有 quality API 可在此补充
  qualityStats.value = { suites: 0, tests: 0 };
  qualityLoading.value = false;
}

async function loadCubeData() {
  try {
    const health = await cubeApi.health();
    cubeHealthy.value = health?.healthy === true;
  } catch {
    cubeHealthy.value = false;
  }

  if (!cubeHealthy.value) {
    cubeLoading.value = false;
    return;
  }

  try {
    const meta = await cubeApi.meta();
    const cubesObj = (meta as any)?.cubes || {};
    const cubeList = Array.isArray(cubesObj) ? cubesObj : Object.values(cubesObj);
    cubeStats.value.cubes = cubeList.length;
    cubeStats.value.measures = cubeList.reduce((sum: number, c: any) => sum + (c?.measures?.length || 0), 0);
  } catch {
    // 获取 meta 失败，保持为 0
  }
  cubeLoading.value = false;
}

function loadSystemStats() {
  // 本地服务器资源（占位数据，实际可通过后端 /system 接口获取）
  systemStats.value = {
    cpu: 0,
    memory: 0,
    disk: 0,
  };
}

function statusType(status: string): TagType {
  const map: Record<string, TagType> = {
    success: "success",
    succeeded: "success",
    failed: "danger",
    running: "warning",
    queued: "info",
    pending: "info",
  };
  return map[status?.toLowerCase()] || "info";
}

function progressColor(percentage: number): string {
  if (percentage >= 90) return "#f56c6c";
  if (percentage >= 70) return "#e6a23c";
  return "#67c23a";
}
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 16px;
}

.section-row {
  margin-bottom: 16px;
}

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

.asset-card {
  .card-loading {
    padding: 8px 0;
  }

  .asset-stats {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .stat-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #ebeef5;

    &:last-child {
      border-bottom: none;
    }
  }

  .stat-label {
    font-size: 14px;
    color: #606266;
  }

  .stat-num {
    font-size: 20px;
    font-weight: bold;
    color: #409eff;
  }
}

.component-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  .comp-name {
    font-size: 14px;
    color: #303133;
  }

  .comp-type {
    font-size: 12px;
    color: #909399;
  }
}

.resource-monitor {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 0;

  .resource-line {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .resource-label {
    font-size: 14px;
    color: #606266;
  }
}
</style>
