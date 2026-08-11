<template>
  <div class="lineage-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据血缘</span>
          <div class="search-bar">
            <el-autocomplete
              v-model="searchQuery"
              :fetch-suggestions="searchEntities"
              placeholder="搜索数据实体名称"
              :prefix-icon="Search"
              clearable
              value-key="name"
              style="width: 350px;"
              @select="handleSelectEntity"
              @keyup.enter="handleManualSearch"
            >
              <template #default="{ item }">
                <div class="suggestion-item">
                  <div class="suggestion-name">{{ item.name }}</div>
                  <small class="suggestion-fqn">{{ item.fullyQualifiedName }}</small>
                </div>
              </template>
            </el-autocomplete>
            <el-button type="primary" @click="handleManualSearch" :loading="loading">查询</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="!omHealthy && !loading"
        type="warning"
        :closable="false"
        style="margin-bottom: 16px;"
      >
        OpenMetadata 组件未连接，请在「系统管理 → 组件配置」中配置 OpenMetadata 组件。
      </el-alert>

      <div v-if="currentEntity" class="current-info">
        <el-tag type="warning" size="large">{{ currentEntity.name }}</el-tag>
        <span class="current-fqn">{{ currentEntity.fullyQualifiedName }}</span>
      </div>

      <el-row :gutter="16" v-loading="loading">
        <el-col :span="17">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="chart-header">
                <span>血缘关系图</span>
                <div class="legend">
                  <span class="legend-item"><i class="dot source"></i>上游</span>
                  <span class="legend-item"><i class="dot target"></i>下游</span>
                  <span class="legend-item"><i class="dot current"></i>当前</span>
                </div>
              </div>
            </template>
            <div ref="chartRef" class="chart-container"></div>
            <el-empty
              v-if="!loading && !currentEntity"
              description="请搜索并选择一个数据实体查看血缘关系"
              :image-size="80"
            />
          </el-card>
        </el-col>

        <el-col :span="7">
          <el-card shadow="never" class="detail-card">
            <template #header>节点详情</template>
            <template v-if="selectedNode">
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="名称">{{ selectedNode.name }}</el-descriptions-item>
                <el-descriptions-item label="全限定名">{{ selectedNode.fullyQualifiedName }}</el-descriptions-item>
                <el-descriptions-item label="类型">
                  <el-tag :type="nodeTypeTagType(selectedNode.nodeType)" size="small">
                    {{ nodeTypeLabel(selectedNode.nodeType) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="描述">{{ selectedNode.description || "无" }}</el-descriptions-item>
              </el-descriptions>

              <div class="detail-section" v-if="selectedNode.upstreamCount !== undefined">
                <span class="detail-label">上游节点数：</span>
                <el-tag type="primary" size="small">{{ selectedNode.upstreamCount }}</el-tag>
              </div>
              <div class="detail-section" v-if="selectedNode.downstreamCount !== undefined">
                <span class="detail-label">下游节点数：</span>
                <el-tag type="success" size="small">{{ selectedNode.downstreamCount }}</el-tag>
              </div>

              <div style="margin-top: 12px;">
                <el-button type="primary" size="small" @click="viewEntityLineage(selectedNode)">
                  查看此节点血缘
                </el-button>
              </div>
            </template>
            <el-empty v-else description="点击图中的节点查看详情" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount, nextTick } from "vue";
import * as echarts from "@/utils/echarts";
import { Search } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useRoute } from "vue-router";
import { openmetadataApi } from "@/api";

type NodeType = "source" | "target" | "current";

interface LineageNode {
  id: string;
  name: string;
  fullyQualifiedName: string;
  description?: string;
  nodeType: NodeType;
  upstreamCount?: number;
  downstreamCount?: number;
}

interface LineageEdge {
  source: string;
  target: string;
}

interface LineageResponse {
  upstream: { nodes: any[]; edges: LineageEdge[] };
  downstream: { nodes: any[]; edges: LineageEdge[] };
}

const chartRef = ref<HTMLElement | null>(null);
const route = useRoute();
const chartInstance = shallowRef<echarts.ECharts | null>(null);

const loading = ref(false);
const omHealthy = ref(false);
const searchQuery = ref("");
const currentEntity = ref<{ name: string; fullyQualifiedName: string; description?: string } | null>(null);
const selectedNode = ref<LineageNode | null>(null);

const nodeColors: Record<NodeType, string> = {
  source: "#409EFF",
  target: "#67C23A",
  current: "#E6A23C",
};

const nodeSizes: Record<NodeType, number> = {
  source: 40,
  target: 40,
  current: 60,
};

function nodeTypeLabel(type: NodeType): string {
  return { source: "上游", target: "下游", current: "当前" }[type];
}

type TagType = "primary" | "success" | "warning" | "info" | "danger";

function nodeTypeTagType(type: NodeType): TagType {
  return ({ source: "primary", target: "success", current: "warning" } as Record<NodeType, TagType>)[type];
}

async function checkHealth() {
  try {
    const res = await openmetadataApi.health();
    omHealthy.value = res?.healthy ?? false;
  } catch {
    omHealthy.value = false;
  }
}

async function searchEntities(query: string, cb: (results: any[]) => void) {
  if (!query.trim() || !omHealthy.value) {
    cb([]);
    return;
  }
  try {
    const res = await openmetadataApi.search(query);
    cb(res || []);
  } catch {
    cb([]);
  }
}

function handleSelectEntity(item: any) {
  currentEntity.value = {
    name: item.name,
    fullyQualifiedName: item.fullyQualifiedName || item.name,
    description: item.description,
  };
  loadLineage(currentEntity.value.fullyQualifiedName);
}

async function handleManualSearch() {
  if (!searchQuery.value.trim()) {
    ElMessage.warning("请输入搜索内容");
    return;
  }
  if (!omHealthy.value) {
    ElMessage.warning("OpenMetadata 未连接");
    return;
  }
  loading.value = true;
  try {
    const res = await openmetadataApi.search(searchQuery.value);
    if (!res || res.length === 0) {
      ElMessage.info("未找到匹配的实体");
      return;
    }
    const first = res[0];
    currentEntity.value = {
      name: first.name,
      fullyQualifiedName: first.fullyQualifiedName || first.name,
      description: first.description,
    };
    await loadLineage(currentEntity.value.fullyQualifiedName);
  } catch {
    /* handled by interceptor */
  } finally {
    loading.value = false;
  }
}

async function loadLineage(fqn: string, entityType = "table") {
  loading.value = true;
  selectedNode.value = null;
  try {
    const res: LineageResponse = await openmetadataApi.lineage(fqn, entityType);
    renderChart(res, fqn);
  } catch {
    /* handled by interceptor */
  } finally {
    loading.value = false;
  }
}

function buildGraphData(lineage: LineageResponse, currentFqn: string) {
  const nodeMap = new Map<string, LineageNode>();
  const edges: { source: string; target: string }[] = [];

  const upstreamNodes = lineage.upstream?.nodes || [];
  const upstreamEdges = lineage.upstream?.edges || [];
  const downstreamNodes = lineage.downstream?.nodes || [];
  const downstreamEdges = lineage.downstream?.edges || [];

  // Current node
  nodeMap.set(currentFqn, {
    id: currentFqn,
    name: currentFqn.split(".").pop() || currentFqn,
    fullyQualifiedName: currentFqn,
    nodeType: "current",
    upstreamCount: upstreamNodes.length,
    downstreamCount: downstreamNodes.length,
  });

  // Upstream nodes
  upstreamNodes.forEach((n: any) => {
    const fqn = n.fullyQualifiedName || n.name;
    if (!nodeMap.has(fqn)) {
      nodeMap.set(fqn, {
        id: fqn,
        name: n.name || fqn.split(".").pop() || fqn,
        fullyQualifiedName: fqn,
        description: n.description,
        nodeType: "source",
      });
    }
  });

  // Downstream nodes
  downstreamNodes.forEach((n: any) => {
    const fqn = n.fullyQualifiedName || n.name;
    if (!nodeMap.has(fqn)) {
      nodeMap.set(fqn, {
        id: fqn,
        name: n.name || fqn.split(".").pop() || fqn,
        fullyQualifiedName: fqn,
        description: n.description,
        nodeType: "target",
      });
    }
  });

  // Upstream edges (flow from upstream → current)
  upstreamEdges.forEach((e: LineageEdge) => {
    edges.push({ source: e.source, target: e.target });
  });

  // Downstream edges (flow from current → downstream)
  downstreamEdges.forEach((e: LineageEdge) => {
    edges.push({ source: e.source, target: e.target });
  });

  // Ensure all edge endpoints exist as nodes (some APIs reference nodes not in the nodes array)
  edges.forEach((e) => {
    if (!nodeMap.has(e.source)) {
      nodeMap.set(e.source, {
        id: e.source,
        name: e.source.split(".").pop() || e.source,
        fullyQualifiedName: e.source,
        nodeType: "source",
      });
    }
    if (!nodeMap.has(e.target)) {
      nodeMap.set(e.target, {
        id: e.target,
        name: e.target.split(".").pop() || e.target,
        fullyQualifiedName: e.target,
        nodeType: "target",
      });
    }
  });

  const nodes = Array.from(nodeMap.values()).map((n) => ({
    id: n.id,
    name: n.name,
    symbolSize: nodeSizes[n.nodeType],
    itemStyle: { color: nodeColors[n.nodeType] },
    label: { show: true, position: "bottom", fontSize: 12 },
    data: n,
  }));

  return { nodes, edges };
}

function renderChart(lineage: LineageResponse, currentFqn: string) {
  if (!chartRef.value) return;

  if (!chartInstance.value) {
    chartInstance.value = echarts.init(chartRef.value);
    chartInstance.value.on("click", handleNodeClick);
  }

  const { nodes, edges } = buildGraphData(lineage, currentFqn);

  const option: echarts.EChartsOption = {
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === "node" && params.data?.data) {
          const d = params.data.data as LineageNode;
          return `<b>${d.name}</b><br/>FQN: ${d.fullyQualifiedName}<br/>类型: ${nodeTypeLabel(d.nodeType)}${d.description ? `<br/>描述: ${d.description}` : ""}`;
        }
        if (params.dataType === "edge") {
          return `${params.data.source} → ${params.data.target}`;
        }
        return params.name;
      },
    },
    series: [
      ({
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        label: { show: true, position: "bottom", fontSize: 12 },
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: [0, 10],
        emphasis: {
          focus: "adjacency",
          lineStyle: { width: 3 },
        },
        force: {
          repulsion: 300,
          edgeLength: 150,
          gravity: 0.1,
        },
        lineStyle: {
          color: "#a0a0a0",
          width: 2,
          curveness: 0.1,
        },
        data: nodes,
        links: edges.map((e) => ({ source: e.source, target: e.target })),
      } as any),
    ],
  };

  chartInstance.value.setOption(option, true);
}

function handleNodeClick(params: any) {
  if (params.dataType === "node" && params.data?.data) {
    selectedNode.value = params.data.data as LineageNode;
  }
}

function viewEntityLineage(node: LineageNode) {
  currentEntity.value = {
    name: node.name,
    fullyQualifiedName: node.fullyQualifiedName,
    description: node.description,
  };
  loadLineage(node.fullyQualifiedName);
}

function handleResize() {
  chartInstance.value?.resize();
}

onMounted(async () => {
  await checkHealth();
  await nextTick();
  if (chartRef.value) {
    chartInstance.value = echarts.init(chartRef.value);
    chartInstance.value.on("click", handleNodeClick);
  }
  window.addEventListener("resize", handleResize);
  const fqn = typeof route.query.fqn === "string" ? route.query.fqn : "";
  const entityType = typeof route.query.type === "string" ? route.query.type : "table";
  if (fqn && omHealthy.value) {
    searchQuery.value = fqn;
    currentEntity.value = { name: fqn.split(".").pop() || fqn, fullyQualifiedName: fqn };
    await loadLineage(fqn, entityType);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chartInstance.value?.dispose();
  chartInstance.value = null;
});
</script>

<style lang="scss" scoped>
.lineage-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .search-bar {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  }

  .current-info {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;

    .current-fqn {
      color: #909399;
      font-size: 13px;
    }
  }

  .chart-card {
    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .legend {
        display: flex;
        gap: 16px;
        font-size: 13px;
        color: #606266;

        .legend-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .dot {
          display: inline-block;
          width: 12px;
          height: 12px;
          border-radius: 50%;

          &.source { background: #409eff; }
          &.target { background: #67c23a; }
          &.current { background: #e6a23c; }
        }
      }
    }

    .chart-container {
      width: 100%;
      height: 550px;
    }
  }

  .detail-card {
    .detail-section {
      margin-top: 12px;
      display: flex;
      align-items: center;
      gap: 8px;

      .detail-label {
        color: #606266;
        font-size: 13px;
      }
    }
  }

  .suggestion-item {
    line-height: 1.4;

    .suggestion-name {
      font-size: 14px;
    }

    .suggestion-fqn {
      color: #909399;
      font-size: 12px;
    }
  }
}
</style>
