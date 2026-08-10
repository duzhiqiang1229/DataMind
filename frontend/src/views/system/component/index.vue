<template>
  <div class="component-config-page">
    <div class="page-header">
      <h2>组件配置</h2>
      <p class="header-desc">配置 DataMind 集成的 6 个外部组件。每个组件有独立的配置项，点击卡片进入配置。</p>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col v-for="code in COMPONENT_ORDER" :key="code" :xs="24" :sm="12" :md="8" :lg="8">
        <el-card class="component-card" shadow="hover" @click="goToDetail(code)">
          <div class="card-body">
            <div class="card-icon" :class="getStatusClass(code)">
              <el-icon :size="32"><component :is="getIcon(schemaMap[code]?.icon)" /></el-icon>
            </div>
            <div class="card-info">
              <div class="card-title-row">
                <span class="card-title">{{ schemaMap[code]?.name }}</span>
                <el-tag size="small" :type="isConfigured(code) ? (getConfig(code)?.status === 'active' ? 'success' : 'info') : 'warning'">
                  {{ isConfigured(code) ? (getConfig(code)?.status === 'active' ? '已配置' : '已停用') : '未配置' }}
                </el-tag>
              </div>
              <div class="card-desc">{{ schemaMap[code]?.description }}</div>
              <div class="card-meta">
                <el-tag size="small" type="info" effect="plain">{{ getTypeLabel(schemaMap[code]?.type) }}</el-tag>
                <template v-if="isConfigured(code)">
                  <span
                    v-if="schemaMap[code]?.hasHttpApi"
                    class="health-indicator"
                    :class="getConfig(code)?.last_check_ok ? 'healthy' : 'unhealthy'"
                  >
                      <el-icon>
                        <CircleCheck v-if="getConfig(code)?.last_check_ok === true" />
                        <CircleClose v-else-if="getConfig(code)?.last_check_ok === false" />
                        <Warning v-else />
                      </el-icon>
                    {{ getConfig(code)?.last_check_ok === true ? '正常' : getConfig(code)?.last_check_ok === false ? '异常' : '未检测' }}
                  </span>
                  <el-tag v-else size="small" type="info" effect="plain">本地工具</el-tag>
                </template>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <span class="footer-label">{{ schemaMap[code]?.hasHttpApi ? (getConfig(code)?.base_url || defaultBaseUrl(code) || '未设置地址') : '本地工具' }}</span>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  Timer, Coin, DataAnalysis, Files, Switch, Cpu,
  ArrowRight, CircleCheck, CircleClose, Warning,
} from "@element-plus/icons-vue";
import { componentApi } from "@/api";
import { COMPONENT_SCHEMAS, COMPONENT_ORDER } from "./component-schemas";

const router = useRouter();
const loading = ref(false);
const configMap = ref<Record<string, any>>({});

const schemaMap = COMPONENT_SCHEMAS;

const iconMap: Record<string, any> = {
  Timer, Coin, DataAnalysis, Files, Switch, Cpu,
};

function getIcon(name?: string) {
  return iconMap[name || ""] || Timer;
}

function isConfigured(code: string): boolean {
  return !!configMap.value[code];
}

function getConfig(code: string) {
  return configMap.value[code];
}

function getStatusClass(code: string): string {
  if (!isConfigured(code)) return "status-unconfigured";
  if (getConfig(code)?.last_check_ok === true) return "status-healthy";
  if (getConfig(code)?.last_check_ok === false) return "status-unhealthy";
  return "status-configured";
}

function getTypeLabel(type?: string): string {
  const labels: Record<string, string> = {
    scheduler: "调度器",
    olap: "OLAP引擎",
    semantic: "语义层",
    governance: "数据治理",
    etl: "数据同步",
    compute: "计算引擎",
  };
  return labels[type || ""] || type || "";
}

function defaultBaseUrl(code: string): string {
  const field = schemaMap[code]?.fields.find((f) => f.key === "base_url");
  return field?.default ? String(field.default) : "";
}

function goToDetail(code: string) {
  router.push(`/system/component/${code}`);
}

async function loadConfigs() {
  loading.value = true;
  try {
    const res = await componentApi.listAll();
    const items = res || [];
    const map: Record<string, any> = {};
    items.forEach((item: any) => {
      map[item.component_code] = item;
    });
    configMap.value = map;
  } catch {
    /* handled */
  } finally {
    loading.value = false;
  }
}

onMounted(loadConfigs);
</script>

<style lang="scss" scoped>
.component-config-page {
  padding: 4px;
}

.page-header {
  margin-bottom: 24px;

  h2 {
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 600;
  }

  .header-desc {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }
}

.component-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 8px;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }

  .card-body {
    display: flex;
    gap: 16px;
    align-items: flex-start;
  }

  .card-icon {
    flex-shrink: 0;
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    &.status-healthy { background: var(--el-color-success); }
    &.status-unhealthy { background: var(--el-color-danger); }
    &.status-configured { background: var(--el-color-primary); }
    &.status-unconfigured { background: var(--el-color-info-light-5); }
  }

  .card-info {
    flex: 1;
    min-width: 0;
  }

  .card-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .card-title {
    font-size: 15px;
    font-weight: 600;
  }

  .card-desc {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.5;
    margin-bottom: 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .health-indicator {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-size: 12px;

    &.healthy { color: var(--el-color-success); }
    &.unhealthy { color: var(--el-color-danger); }
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--el-border-color-lighter);

    .footer-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 200px;
    }

    .arrow-icon {
      color: var(--el-text-color-placeholder);
    }
  }
}
</style>
