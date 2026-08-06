<template>
  <div class="metrics-center">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>指标中心</span>
          <el-button :icon="Refresh" size="small" @click="loadMeta" :loading="loading">刷新</el-button>
        </div>
      </template>

      <el-alert v-if="!cubeHealthy && !loading" type="warning" :closable="false" style="margin-bottom: 16px;">
        Cube 组件未连接，请在「系统管理 → 组件配置」中配置 Cube 组件。
      </el-alert>

      <el-row :gutter="16">
        <el-col :span="8" v-for="cube in cubes" :key="cube.name">
          <el-card shadow="hover" style="margin-bottom: 16px;">
            <template #header>{{ cube.title || cube.name }}</template>
            <div class="cube-info">
              <p v-if="cube.description">{{ cube.description }}</p>
              <div v-if="cube.measures && cube.measures.length">
                <strong>度量:</strong>
                <el-tag v-for="m in cube.measures" :key="m.name" size="small" style="margin: 2px;">
                  {{ m.title || m.name }}
                </el-tag>
              </div>
              <div v-if="cube.dimensions && cube.dimensions.length" style="margin-top: 8px;">
                <strong>维度:</strong>
                <el-tag v-for="d in cube.dimensions" :key="d.name" size="small" type="info" style="margin: 2px;">
                  {{ d.title || d.name }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="!loading && cubes.length === 0" description="暂无指标数据" />
    </el-card>

    <!-- 指标查询 -->
    <el-card style="margin-top: 16px;" v-if="cubeHealthy">
      <template #header>指标查询</template>
      <el-form :inline="true" label-width="80px">
        <el-form-item label="度量">
          <el-select v-model="query.measures" multiple filterable placeholder="选择度量" style="width: 300px;">
            <el-option v-for="m in allMeasures" :key="m.name" :label="m.title || m.name" :value="m.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="维度">
          <el-select v-model="query.dimensions" multiple filterable placeholder="选择维度" style="width: 300px;">
            <el-option v-for="d in allDimensions" :key="d.name" :label="d.title || d.name" :value="d.name" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="executeQuery" :loading="querying">查询</el-button>
        </el-form-item>
      </el-form>

      <div v-if="queryResult">
        <el-table :data="queryResult.data || []" border size="small" style="margin-top: 12px;">
          <el-table-column
            v-for="col in (queryResult.annotation?.columns || queryResult.data?.[0] ? Object.keys(queryResult.data[0]) : [])"
            :key="col"
            :prop="col"
            :label="col"
            min-width="120"
            show-overflow-tooltip
          />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { cubeApi } from "@/api";

const loading = ref(false);
const querying = ref(false);
const cubeHealthy = ref(false);
const metaData = ref<any>(null);

const cubes = computed(() => {
  if (!metaData.value?.cubes) return [];
  return Object.entries(metaData.value.cubes).map(([name, data]: [string, any]) => ({ name, ...data }));
});

const allMeasures = computed(() => cubes.value.flatMap((c: any) => c.measures || []));
const allDimensions = computed(() => cubes.value.flatMap((c: any) => c.dimensions || []));

const query = reactive({
  measures: [] as string[],
  dimensions: [] as string[],
});

const queryResult = ref<any>(null);

async function loadMeta() {
  loading.value = true;
  try {
    const [health, meta] = await Promise.all([
      cubeApi.health(),
      cubeApi.meta().catch(() => null),
    ]);
    cubeHealthy.value = health?.healthy || false;
    if (meta) metaData.value = meta;
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

async function executeQuery() {
  if (query.measures.length === 0) {
    ElMessage.warning("请选择至少一个度量");
    return;
  }
  querying.value = true;
  try {
    queryResult.value = await cubeApi.load(query);
    ElMessage.success("查询成功");
  } catch { /* handled */ } finally {
    querying.value = false;
  }
}

onMounted(loadMeta);
</script>

<style lang="scss" scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.cube-info p { color: #909399; font-size: 13px; margin-bottom: 8px; }
</style>
