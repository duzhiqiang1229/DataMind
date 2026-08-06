<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>存储监控</span>
        <el-button :icon="Refresh" @click="loadOverview" :loading="loading">刷新</el-button>
      </div>
    </template>

    <el-alert
      v-if="showNotConfigured"
      title="Doris 未配置或不可用，请先在系统组件管理中配置 Doris 连接。"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    />

    <!-- Row 1: 汇总统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="6" v-for="stat in statCards" :key="stat.label">
        <el-card shadow="hover">
          <div class="stat-card">
            <el-icon :size="28" :color="stat.color">
              <component :is="stat.icon" />
            </el-icon>
            <div>
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Row 2: 数据库存储概览 -->
    <h4 class="section-title">数据库存储概览</h4>
    <el-table
      :data="overviewData"
      v-loading="loading"
      border
      style="width: 100%;"
      @row-click="onDatabaseClick"
      highlight-current-row
      :row-class-name="dbRowClass"
    >
      <el-table-column prop="database" label="数据库" min-width="180" show-overflow-tooltip />
      <el-table-column prop="table_count" label="表数量" width="120" align="right" />
      <el-table-column prop="total_rows" label="总行数" width="160" align="right">
        <template #default="{ row }">
          {{ formatNumber(row.total_rows) }}
        </template>
      </el-table-column>
      <el-table-column prop="size_mb" label="大小 (MB)" width="140" align="right">
        <template #default="{ row }">
          {{ formatSize(row.size_mb) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            size="small"
            type="primary"
            link
            @click.stop="onDatabaseClick(row)"
          >
            {{ selectedDatabase === row.database ? '收起' : '查看表' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Row 3: 选中数据库的表列表 -->
    <div v-if="selectedDatabase" style="margin-top: 24px;">
      <h4 class="section-title">
        {{ selectedDatabase }} - 表列表
        <el-button
          size="small"
          :icon="Refresh"
          link
          @click="loadTableStats"
          :loading="tablesLoading"
        />
      </h4>
      <el-table :data="tableStatsList" v-loading="tablesLoading" border size="small">
        <el-table-column prop="name" label="表名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="engine" label="引擎" width="120" show-overflow-tooltip />
        <el-table-column label="行数" width="140" align="right">
          <template #default="{ row }">
            {{ formatNumber(row.rows) }}
          </template>
        </el-table-column>
        <el-table-column label="数据大小" width="140" align="right">
          <template #default="{ row }">
            {{ formatSize(row.data_size) }}
          </template>
        </el-table-column>
        <el-table-column label="列数" width="100" align="right">
          <template #default="{ row }">
            {{ getColumnCount(row) }}
          </template>
        </el-table-column>
        <el-table-column label="分区数" width="100" align="right">
          <template #default="{ row }">
            {{ getPartitionCount(row) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openTableDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!tablesLoading && tableStatsList.length === 0" style="text-align: center; padding: 20px; color: #909399;">
        暂无表数据
      </div>
    </div>

    <!-- 表详情 Dialog -->
    <el-dialog
      v-model="tableDetailDialog"
      :title="`表详情 - ${currentTableDetail?.name ?? ''}`"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <div v-loading="detailLoading">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px;">
          <el-descriptions-item label="表名">{{ currentTableDetail?.name }}</el-descriptions-item>
          <el-descriptions-item label="引擎">{{ currentTableDetail?.engine || '-' }}</el-descriptions-item>
          <el-descriptions-item label="行数">{{ formatNumber(currentTableDetail?.rows) }}</el-descriptions-item>
          <el-descriptions-item label="数据大小">{{ formatSize(currentTableDetail?.data_size) }}</el-descriptions-item>
          <el-descriptions-item label="列数">{{ getColumnCount(currentTableDetail) }}</el-descriptions-item>
          <el-descriptions-item label="分区数">{{ getPartitionCount(currentTableDetail) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 列信息 -->
        <h4 class="section-title">列信息</h4>
        <el-table :data="currentTableDetail?.columns || []" border size="small" style="margin-bottom: 16px;">
          <el-table-column prop="name" label="列名" min-width="180" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="160" show-overflow-tooltip />
          <el-table-column prop="comment" label="注释" min-width="200" show-overflow-tooltip />
        </el-table>
        <div
          v-if="!currentTableDetail?.columns || currentTableDetail.columns.length === 0"
          style="text-align: center; padding: 20px; color: #909399;"
        >
          暂无列信息
        </div>

        <!-- 分区信息 -->
        <h4 class="section-title">分区信息</h4>
        <el-table :data="partitions" v-loading="partitionsLoading" border size="small">
          <el-table-column prop="name" label="分区名" min-width="200" show-overflow-tooltip />
          <el-table-column label="行数" width="140" align="right">
            <template #default="{ row }">
              {{ formatNumber(row.rows) }}
            </template>
          </el-table-column>
          <el-table-column label="数据大小" width="140" align="right">
            <template #default="{ row }">
              {{ formatSize(row.data_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="last_update_time" label="最后更新时间" min-width="180" show-overflow-tooltip />
          <el-table-column prop="state" label="状态" width="100" />
        </el-table>
        <div
          v-if="!partitionsLoading && partitions.length === 0"
          style="text-align: center; padding: 20px; color: #909399;"
        >
          暂无分区信息（该表可能未分区）
        </div>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { dorisStorageApi } from "@/api";

const loading = ref(false);
const showNotConfigured = ref(false);
const overviewData = ref<any[]>([]);

const selectedDatabase = ref("");
const tableStatsList = ref<any[]>([]);
const tablesLoading = ref(false);

const tableDetailDialog = ref(false);
const currentTableDetail = ref<any>(null);
const detailLoading = ref(false);
const partitions = ref<any[]>([]);
const partitionsLoading = ref(false);

const statCards = reactive([
  { label: "数据库总数", value: 0, icon: "Coin", color: "#409eff" },
  { label: "表总数", value: 0, icon: "Files", color: "#67c23a" },
  { label: "总行数", value: "0", icon: "DataLine", color: "#e6a23c" },
  { label: "总大小", value: "0 MB", icon: "Box", color: "#f56c6c" },
]);

onMounted(loadOverview);

async function loadOverview() {
  loading.value = true;
  showNotConfigured.value = false;
  selectedDatabase.value = "";
  tableStatsList.value = [];
  try {
    const res = await dorisStorageApi.overview();
    const list = Array.isArray(res) ? res : res?.items || res?.databases || [];
    overviewData.value = list;
    if (list.length === 0) {
      showNotConfigured.value = true;
    }
    // 汇总统计
    const dbCount = list.length;
    const tableCount = list.reduce((sum: number, d: any) => sum + (Number(d.table_count) || 0), 0);
    const totalRows = list.reduce((sum: number, d: any) => sum + (Number(d.total_rows) || 0), 0);
    const totalSize = list.reduce((sum: number, d: any) => sum + (Number(d.size_mb) || 0), 0);
    statCards[0].value = dbCount;
    statCards[1].value = tableCount;
    statCards[2].value = formatNumber(totalRows);
    statCards[3].value = formatSize(totalSize);
  } catch (e: any) {
    showNotConfigured.value = true;
    overviewData.value = [];
    statCards[0].value = 0;
    statCards[1].value = 0;
    statCards[2].value = "0";
    statCards[3].value = "0 MB";
  } finally {
    loading.value = false;
  }
}

async function onDatabaseClick(row: any) {
  if (selectedDatabase.value === row.database) {
    // 收起
    selectedDatabase.value = "";
    tableStatsList.value = [];
    return;
  }
  selectedDatabase.value = row.database;
  await loadTableStats();
}

async function loadTableStats() {
  if (!selectedDatabase.value) return;
  tablesLoading.value = true;
  tableStatsList.value = [];
  try {
    // overviewData 中已有该库下的信息，但需要获取每张表的详情。
    // 调用 tableStats 需要表名，先从概览中拿不到单表列表。
    // 这里通过遍历 overview 项中可能的 tables 字段获取，若无则提示。
    const dbEntry = overviewData.value.find((d) => d.database === selectedDatabase.value);
    const tables: any[] = dbEntry?.tables || dbEntry?.table_list || [];
    if (tables.length > 0) {
      tableStatsList.value = tables;
    } else {
      // 尝试逐表获取 stats（如果概览里有表名列表）
      const tableNames: string[] = (dbEntry?.table_names || []).map((t: any) =>
        typeof t === "string" ? t : t.name
      );
      const results = await Promise.all(
        tableNames.map((name) =>
          dorisStorageApi
            .tableStats(selectedDatabase.value, name)
            .then((s) => ({ ...s, name }))
            .catch(() => null)
        )
      );
      tableStatsList.value = results.filter(Boolean);
      if (tableNames.length === 0) {
        ElMessage.warning("该数据库未返回表列表，无法加载表统计");
      }
    }
  } catch (e: any) {
    ElMessage.error(`加载表统计失败: ${e?.message || e}`);
  } finally {
    tablesLoading.value = false;
  }
}

async function openTableDetail(table: any) {
  currentTableDetail.value = table;
  partitions.value = [];
  tableDetailDialog.value = true;
  detailLoading.value = true;
  partitionsLoading.value = true;
  try {
    // 如果当前 table 只有部分字段，尝试获取完整 stats
    if (!table.columns && !table.data_size) {
      try {
        const full = await dorisStorageApi.tableStats(selectedDatabase.value, table.name);
        currentTableDetail.value = { ...table, ...full };
      } catch {
        // keep as-is
      }
    }
  } finally {
    detailLoading.value = false;
  }
  try {
    const pres = await dorisStorageApi.partitions(selectedDatabase.value, table.name);
    partitions.value = Array.isArray(pres) ? pres : pres?.items || pres?.partitions || [];
  } catch (e: any) {
    partitions.value = [];
  } finally {
    partitionsLoading.value = false;
  }
}

function dbRowClass({ row }: { row: any }): string {
  return selectedDatabase.value === row.database ? "current-row" : "";
}

function getColumnCount(row: any): number | string {
  if (!row) return "-";
  if (Array.isArray(row.columns)) return row.columns.length;
  if (row.column_count != null) return row.column_count;
  return "-";
}

function getPartitionCount(row: any): number | string {
  if (!row) return "-";
  if (Array.isArray(row.partitions)) return row.partitions.length;
  if (row.partition_count != null) return row.partition_count;
  return "-";
}

function formatNumber(n: any): string {
  if (n == null || n === "" || isNaN(Number(n))) return "-";
  const num = Number(n);
  if (num >= 1e8) return (num / 1e8).toFixed(2) + " 亿";
  if (num >= 1e4) return (num / 1e4).toFixed(2) + " 万";
  return num.toLocaleString();
}

function formatSize(mb: any): string {
  if (mb == null || mb === "" || isNaN(Number(mb))) return "-";
  const size = Number(mb);
  if (size >= 1024) return (size / 1024).toFixed(2) + " GB";
  if (size >= 1) return size.toFixed(2) + " MB";
  return (size * 1024).toFixed(2) + " KB";
}
</script>

<style lang="scss" scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-value {
  font-size: 22px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.section-title {
  margin: 8px 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-table__row.current-row) {
  background-color: var(--el-color-primary-light-9) !important;
}
</style>
