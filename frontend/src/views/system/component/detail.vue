<template>
  <div class="component-detail-page">
    <!-- breadcrumb + header -->
    <el-page-header @back="goBack" class="page-header">
      <template #content>
        <div class="header-content">
          <el-icon :size="20" class="header-icon"><component :is="getIcon(schema?.icon)" /></el-icon>
          <span class="header-title">{{ schema?.name }}</span>
          <el-tag v-if="config" size="small" :type="config.status === 'active' ? 'success' : 'info'">
            {{ config.status === 'active' ? '已启用' : '已停用' }}
          </el-tag>
        </div>
      </template>
    </el-page-header>

    <el-card v-loading="loading" class="config-card">
      <template #header>
        <div class="card-header">
          <span>{{ schema?.description }}</span>
          <div class="header-actions" v-if="schema?.hasHttpApi">
            <el-button type="success" :icon="Connection" :loading="checking" @click="handleHealthCheck">
              连接测试
            </el-button>
            <el-button v-if="code === 'airflow'" type="primary" :icon="Upload" :loading="deploying" @click="handleDeployDags">
              部署 DAG
            </el-button>
          </div>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        label-width="150px"
        label-position="right"
        class="config-form"
      >
        <div v-for="group in groupFields" :key="group.key" class="form-group">
          <div class="group-title">
            <span class="group-title-icon">
              <el-icon :size="14">
                <Connection v-if="group.key === 'connection'" />
                <Lock v-else-if="group.key === 'credentials'" />
                <Setting v-else />
              </el-icon>
            </span>
            <span class="group-title-text">{{ group.label }}</span>
          </div>

          <el-form-item
            v-for="field in group.fields"
            :key="field.key"
            :label="field.label"
            :prop="field.key"
            :rules="fieldRules(field)"
          >
            <el-input
              v-if="field.type === 'text'"
              v-model="formData[field.key]"
              :placeholder="field.placeholder"
              :type="field.key.includes('password') ? 'password' : undefined"
              :show-password="field.key.includes('password')"
              clearable
            />
            <el-input-number
              v-else-if="field.type === 'number'"
              v-model="formData[field.key]"
              :placeholder="field.placeholder"
              :min="field.min"
              :max="field.max"
              :controls="false"
              style="width: 100%"
            />
            <el-input
              v-else-if="field.type === 'password'"
              v-model="formData[field.key]"
              type="password"
              show-password
              :placeholder="field.placeholder"
              clearable
            />
            <el-select
              v-else-if="field.type === 'select'"
              v-model="formData[field.key]"
              style="width: 100%"
              :placeholder="field.placeholder || '请选择'"
            >
              <el-option
                v-for="opt in (field.dynamicOptions === 'datasources' ? datasourceOptions : field.options || [])"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <div
              v-if="field.dynamicOptions === 'datasources' && datasourceOptions.length === 0"
              class="field-help"
            >
              <el-icon :size="12"><InfoFilled /></el-icon>
              暂无已连接的数据源，请先在「数据管理 → 数据源管理」中新增并测试连接。
            </div>
            <el-input
              v-else-if="field.type === 'textarea'"
              v-model="formData[field.key]"
              type="textarea"
              :rows="3"
              :placeholder="field.placeholder"
            />
            <div v-if="field.help" class="field-help">
              <el-icon :size="12"><InfoFilled /></el-icon>
              {{ field.help }}
            </div>
          </el-form-item>
        </div>

        <!-- status toggle -->
        <div class="form-group">
          <div class="group-title">
            <span class="group-title-icon"><el-icon :size="14"><CircleCheck /></el-icon></span>
            <span class="group-title-text">启用状态</span>
          </div>
          <el-form-item label="启用组件">
            <el-switch v-model="formData._status" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </div>
      </el-form>

      <!-- save buttons -->
      <div class="form-footer">
        <div class="footer-status" v-if="config?.last_check_at">
          <span class="footer-status-label">上次检测</span>
          <el-tag :type="config.last_check_ok ? 'success' : 'danger'" size="small" effect="plain">
            {{ config.last_check_ok ? '正常' : '异常' }}
          </el-tag>
          <span class="footer-status-time">{{ formatTime(config.last_check_at) }}</span>
        </div>
        <div class="footer-buttons">
          <el-button @click="goBack">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, type FormInstance } from "element-plus";
import {
  Timer, Coin, DataAnalysis, Files, Switch, Cpu,
  Connection, Lock, Setting, CircleCheck, InfoFilled, Upload,
} from "@element-plus/icons-vue";
import { componentApi, airflowApi, datasourceApi } from "@/api";
import { formatDateTime } from "@/utils/format";
import { COMPONENT_SCHEMAS, type ComponentSchema, type FormField } from "./component-schemas";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const checking = ref(false);
const deploying = ref(false);
const config = ref<any>(null);
const formData = reactive<Record<string, any>>({});
const datasourceOptions = ref<{ label: string; value: string }[]>([]);
const formRef = ref<FormInstance>();

const code = computed(() => route.params.code as string);
const schema = computed<ComponentSchema | undefined>(() => COMPONENT_SCHEMAS[code.value]);

const iconMap: Record<string, any> = { Timer, Coin, DataAnalysis, Files, Switch, Cpu };
function getIcon(name?: string) {
  return iconMap[name || ""] || Timer;
}

/** Fields visible based on auth_type condition */
const visibleFields = computed<FormField[]>(() => {
  if (!schema.value) return [];
  return schema.value.fields.filter((f) => {
    if (f.showWhenAuth) {
      return formData.auth_type === f.showWhenAuth;
    }
    return true;
  });
});

const groupFields = computed(() => {
  if (!schema.value) return [];
  const groups = [
    { key: "connection", label: "连接信息", fields: [] as FormField[] },
    { key: "credentials", label: "凭据信息", fields: [] as FormField[] },
    { key: "advanced", label: "高级配置", fields: [] as FormField[] },
  ];
  visibleFields.value.forEach((f) => {
    const g = groups.find((x) => x.key === f.group);
    if (g) g.fields.push(f);
  });
  return groups.filter((g) => g.fields.length > 0);
});

function fieldRules(field: FormField) {
  const rules: any[] = [];
  if (field.required) {
    rules.push({ required: true, message: `请输入${field.label}`, trigger: "blur" });
  }
  if (field.type === "number") {
    rules.push({
      validator: (_rule: any, value: any, callback: any) => {
        if (value === undefined || value === null || value === "") return callback();
        const n = Number(value);
        if (Number.isNaN(n)) return callback(new Error(`${field.label}必须是数字`));
        if (field.min !== undefined && n < field.min) {
          return callback(new Error(`${field.label}不能小于 ${field.min}`));
        }
        if (field.max !== undefined && n > field.max) {
          return callback(new Error(`${field.label}不能大于 ${field.max}`));
        }
        callback();
      },
      trigger: "blur",
    });
  }
  if (field.pattern) {
    rules.push({
      pattern: field.pattern,
      message: field.patternMessage || `${field.label}格式不正确`,
      trigger: "blur",
    });
  }
  return rules;
}

function formatTime(iso: string | null | undefined): string {
  return formatDateTime(iso);
}

function initForm() {
  if (!schema.value) return;
  schema.value.fields.forEach((f) => {
    formData[f.key] = f.default;
  });
  formData.auth_type = schema.value.fields.find((f) => f.store === "auth_type")?.default || "none";
  formData._status = true;
}

async function loadConfig() {
  if (!schema.value) return;
  loading.value = true;
  try {
    const res = await componentApi.getByCode(code.value);
    if (res) {
      config.value = res;
      // populate form from loaded config
      formData.base_url = res.base_url || "";
      formData.auth_type = res.auth_type || "none";
      formData._status = res.status === "active";

      // populate config_json fields
      if (res.config_json) {
        schema.value.fields.forEach((f) => {
          if (f.store === "config" && res.config_json[f.key] !== undefined) {
            formData[f.key] = res.config_json[f.key];
          }
        });
      }
      // populate credentials fields (real passwords stay masked in password inputs)
      if (res.credentials) {
        schema.value.fields.forEach((f) => {
          if (f.store === "credentials" && res.credentials[f.key] !== undefined) {
            formData[f.key] = res.credentials[f.key];
          }
        });
      }
    } else {
      config.value = null;
      initForm();
    }
  } catch {
    config.value = null;
    initForm();
  } finally {
    loading.value = false;
  }
}

async function loadDatasourceOptions() {
  if (!schema.value?.fields.some((f) => f.dynamicOptions === "datasources")) return;
  try {
    const res = await datasourceApi.list({ page: 1, page_size: 100, status: "active" });
    const items = res.items || [];
    datasourceOptions.value = items
      .filter((d: any) => d.last_connection_ok === true)
      .map((d: any) => ({ label: d.source_name, value: d.id }));
  } catch {
    datasourceOptions.value = [];
  }
}

async function handleSave() {
  if (!schema.value) return;
  if (formRef.value) {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
  }
  saving.value = true;
  try {
    // Build config_json from fields with store="config"
    const configJson: Record<string, any> = {};
    schema.value.fields.forEach((f) => {
      if (f.store === "config") {
        // convert number fields
        if (f.type === "number") {
          configJson[f.key] = Number(formData[f.key]);
        } else {
          configJson[f.key] = formData[f.key];
        }
      }
    });

    // Build credentials from fields with store="credentials"
    const credentials: Record<string, any> = {};
    let hasCreds = false;
    schema.value.fields.forEach((f) => {
      if (f.store === "credentials" && formData[f.key]) {
        credentials[f.key] = formData[f.key];
        hasCreds = true;
      }
    });

    const payload: any = {
      component_name: schema.value.name,
      config_json: configJson,
      auth_type: formData.auth_type || "none",
      status: formData._status ? "active" : "inactive",
    };

    // set base_url if component has HTTP API
    if (schema.value.hasHttpApi) {
      payload.base_url = formData.base_url || "";
    }

    if (hasCreds) {
      payload.credentials = credentials;
    }

    await componentApi.upsertByCode(code.value, payload);
    ElMessage.success("配置保存成功");
    await loadConfig();
  } catch (e: any) {
    ElMessage.error(e?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleHealthCheck() {
  if (!code.value) return;
  checking.value = true;
  try {
    const res = await componentApi.healthCheck(code.value);
    if (res.healthy) {
      ElMessage.success(`${schema.value?.name} 连接正常`);
    } else {
      ElMessage.error(`${schema.value?.name} 连接失败: ${res.message || ''}`);
    }
    await loadConfig();
  } catch (e: any) {
    ElMessage.error(e?.message || "连接测试失败");
  } finally {
    checking.value = false;
  }
}

async function handleDeployDags() {
  deploying.value = true;
  try {
    const res = await airflowApi.deployDags();
    const list = (res?.uploaded || []).map((p: string) => p.split("/").pop()).join(", ");
    ElMessage.success(`DAG 模板已部署到 ${res?.dags_path || ""}（${list}）`);
  } catch (e: any) {
    ElMessage.error(e?.message || "部署 DAG 失败");
  } finally {
    deploying.value = false;
  }
}

function goBack() {
  router.push("/system/component");
}

watch(() => route.params.code, () => {
  initForm();
  loadConfig();
});

onMounted(() => {
  initForm();
  loadConfig();
  loadDatasourceOptions();
});
</script>

<style lang="scss" scoped>
.component-detail-page {
  .page-header {
    margin-bottom: 20px;
  }

  .header-content {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-icon {
    color: var(--el-color-primary);
  }

  .header-title {
    font-size: 18px;
    font-weight: 600;
  }

  .config-card {
    max-width: 780px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .config-form {
    .form-group {
      background: var(--el-fill-color-lighter);
      border: 1px solid var(--el-border-color-lighter);
      border-radius: 8px;
      padding: 4px 20px 8px;
      margin-bottom: 16px;

      .group-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        margin: 12px 0 8px;

        .group-title-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          border-radius: 6px;
          background: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
        }
      }
    }

    .field-help {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 6px;
      line-height: 1.4;
    }
  }

  .form-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-lighter);

    .footer-status {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--el-text-color-secondary);

      .footer-status-label {
        color: var(--el-text-color-regular);
      }
    }

    .footer-buttons {
      display: flex;
      gap: 12px;
    }
  }
}
</style>
