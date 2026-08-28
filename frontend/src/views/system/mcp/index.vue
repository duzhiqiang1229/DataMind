<template>
  <div class="mcp-page">
    <div class="page-header">
      <div>
        <h2>MCP管理</h2>
        <p>让外部 Agent 通过受控工具完成建模、开发、指标、调度和数据服务建设。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建客户端</el-button>
    </div>

    <el-alert type="info" :closable="false" show-icon class="endpoint-alert">
      <template #title>Streamable HTTP 地址：<el-text tag="code">{{ mcpEndpoint }}</el-text></template>
      支持数据建模、SQL预览、Airflow调度、物理表目录、运行血缘、数据质量、Cube建模、指标建设和数据服务。写操作先进入变更集；执行和发布类操作均需明确确认。
    </el-alert>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="变更集中心" name="changes"><ChangeSetCenter ref="changeSetCenterRef" /></el-tab-pane>
      <el-tab-pane label="功能清单" name="capabilities">
        <div class="capability-toolbar">
          <el-input v-model="capabilityKeyword" clearable placeholder="搜索工具名称、说明或授权范围" style="width:360px" />
          <el-select v-model="moduleFilter" clearable placeholder="全部模块" style="width:160px">
            <el-option v-for="module in capabilityModules" :key="module" :label="module" :value="module" />
          </el-select>
          <span class="capability-total">共 {{ filteredCapabilities.length }} / {{ capabilities.length }} 个工具</span>
        </div>
        <el-table v-loading="capabilityLoading" :data="filteredCapabilities" border stripe>
          <el-table-column prop="module" label="模块" width="110" />
          <el-table-column prop="name" label="工具名称" min-width="220"><template #default="{ row }"><el-text tag="code">{{ row.name }}</el-text></template></el-table-column>
          <el-table-column prop="description" label="功能说明" min-width="310" show-overflow-tooltip />
          <el-table-column prop="scope" label="所需授权" min-width="175"><template #default="{ row }"><el-tag size="small" effect="plain">{{ row.scope || '-' }}</el-tag></template></el-table-column>
          <el-table-column label="风险" width="85" align="center"><template #default="{ row }"><el-tag size="small" :type="riskTag(row.risk_level)">{{ riskLabel(row.risk_level) }}</el-tag></template></el-table-column>
          <el-table-column label="人工确认" width="95" align="center"><template #default="{ row }"><el-tag size="small" :type="row.confirmation_required ? 'warning' : 'info'">{{ row.confirmation_required ? '需要' : '不需要' }}</el-tag></template></el-table-column>
          <el-table-column label="参数" min-width="230"><template #default="{ row }"><div class="parameter-list"><el-tag v-for="parameter in row.parameters" :key="parameter.name" size="small" :type="parameter.required ? 'primary' : 'info'" effect="plain">{{ parameter.name }}{{ parameter.required ? '*' : '' }}</el-tag><span v-if="!row.parameters.length">无</span></div></template></el-table-column>
        </el-table>
        <el-empty v-if="!capabilityLoading && !filteredCapabilities.length" description="没有匹配的 MCP 工具" />
      </el-tab-pane>
      <el-tab-pane label="客户端与凭证" name="clients">
        <el-table v-loading="loading" :data="clients" border>
          <el-table-column prop="client_name" label="客户端" min-width="160" />
          <el-table-column prop="client_code" label="编码" min-width="150" />
          <el-table-column label="授权范围" min-width="330">
            <template #default="{ row }">
              <el-tag v-for="scope in row.scopes" :key="scope" size="small" effect="plain" class="scope-tag">{{ scope }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最近连接" width="170">
            <template #default="{ row }">{{ formatDateTime(row.last_connected_at) || "尚未连接" }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === "active" ? "启用" : "停用" }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }"><el-button link type="primary" @click="openScopes(row)">编辑授权</el-button><el-button link type="primary" @click="openTokens(row)">管理凭证</el-button></template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && !clients.length" description="尚未创建 MCP 客户端" />
      </el-tab-pane>

      <el-tab-pane label="工具调用审计" name="audit">
        <el-table v-loading="auditLoading" :data="toolCalls" border>
          <el-table-column prop="tool_name" label="工具" min-width="190" />
          <el-table-column label="结果" width="90">
            <template #default="{ row }"><el-tag :type="row.status === 'success' ? 'success' : 'danger'">{{ row.status === "success" ? "成功" : "失败" }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="elapsed_ms" label="耗时(ms)" width="100" />
          <el-table-column label="参数" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">{{ JSON.stringify(row.arguments || {}) }}</template>
          </el-table-column>
          <el-table-column label="调用时间" width="170"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createVisible" title="新建 MCP 客户端" width="560px">
      <el-form ref="createFormRef" :model="createForm" :rules="rules" label-width="100px">
        <el-form-item label="客户端名称" prop="client_name"><el-input v-model="createForm.client_name" placeholder="例如：数据建模 Agent" /></el-form-item>
        <el-form-item label="客户端编码" prop="client_code"><el-input v-model="createForm.client_code" placeholder="例如：modeling_agent" /></el-form-item>
        <el-form-item label="服务用户" prop="service_user_id">
          <el-select v-model="createForm.service_user_id" filterable style="width:100%" placeholder="Agent 操作将以该用户身份审计">
            <el-option v-for="user in users" :key="user.id" :label="`${user.full_name || user.username} (${user.username})`" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权范围">
          <el-checkbox-group v-model="createForm.scopes">
            <el-checkbox v-for="scope in scopeOptions" :key="scope" :value="scope">{{ scope }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="createVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="createClient">创建</el-button></template>
    </el-dialog>

    <el-drawer v-model="tokenVisible" :title="`${selectedClient?.client_name || ''} · 凭证`" size="620px">
      <div class="token-toolbar"><el-button type="primary" :icon="Key" @click="tokenCreateVisible=true">生成 Token</el-button></div>
      <el-table v-loading="tokenLoading" :data="tokens" border>
        <el-table-column prop="token_name" label="名称" min-width="130" />
        <el-table-column prop="token_prefix" label="Token 前缀" min-width="150" />
        <el-table-column label="最近使用" width="165"><template #default="{ row }">{{ formatDateTime(row.last_used_at) || "未使用" }}</template></el-table-column>
        <el-table-column label="状态" width="85"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === "active" ? "有效" : "已吊销" }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="85"><template #default="{ row }"><el-button v-if="row.status === 'active'" link type="danger" @click="revoke(row)">吊销</el-button></template></el-table-column>
      </el-table>
    </el-drawer>

    <el-dialog v-model="scopeVisible" title="编辑授权范围" width="520px">
      <el-checkbox-group v-model="editingScopes" class="scope-editor">
        <el-checkbox v-for="scope in scopeOptions" :key="scope" :value="scope">{{ scope }}</el-checkbox>
      </el-checkbox-group>
      <template #footer><el-button @click="scopeVisible=false">取消</el-button><el-button type="primary" :loading="scopeSubmitting" @click="saveScopes">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="tokenCreateVisible" title="生成 MCP Token" width="460px">
      <el-form label-width="90px"><el-form-item label="凭证名称"><el-input v-model="tokenName" placeholder="例如：Codex 开发环境" /></el-form-item></el-form>
      <template #footer><el-button @click="tokenCreateVisible=false">取消</el-button><el-button type="primary" :loading="tokenSubmitting" @click="issueToken">生成</el-button></template>
    </el-dialog>

    <el-dialog v-model="secretVisible" title="MCP Token 已生成" width="620px" :close-on-click-modal="false">
      <el-alert title="Token 只展示一次，请立即复制并妥善保存。DataMind 不保存可恢复的明文。" type="warning" :closable="false" show-icon />
      <div class="secret-box"><el-input :model-value="oneTimeSecret" readonly /><el-button type="primary" @click="copySecret">复制</el-button></div>
      <template #footer><el-button type="primary" @click="closeSecret">我已保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance } from "element-plus";
import { Key, Plus } from "@element-plus/icons-vue";
import { mcpManagementApi, userApi } from "@/api";
import { formatDateTime } from "@/utils/format";
import ChangeSetCenter from "./change-set-center.vue";

const scopeOptions = [
  "metadata:read", "modeling:read", "modeling:draft",
  "development:read", "development:draft", "metrics:read", "metrics:draft", "metrics:execute",
  "development:execute", "scheduling:read", "scheduling:write", "scheduling:execute",
  "lineage:read", "changeset:draft", "changeset:commit",
  "data_service:read", "data_service:draft", "data_service:execute",
  "data_service:publish", "data_service:credentials", "data_service:monitor",
  "catalog:read", "catalog:sync", "quality:read", "quality:draft", "quality:execute",
];
const activeTab = ref("changes");
const changeSetCenterRef = ref<InstanceType<typeof ChangeSetCenter>>();
const clients = ref<any[]>([]); const users = ref<any[]>([]); const toolCalls = ref<any[]>([]); const tokens = ref<any[]>([]);
const capabilities = ref<any[]>([]); const capabilityModules = ref<string[]>([]); const capabilityKeyword = ref(""); const moduleFilter = ref("");
const loading = ref(false); const auditLoading = ref(false); const capabilityLoading = ref(false); const tokenLoading = ref(false); const submitting = ref(false); const tokenSubmitting = ref(false);
const createVisible = ref(false); const tokenVisible = ref(false); const tokenCreateVisible = ref(false); const secretVisible = ref(false); const scopeVisible = ref(false); const scopeSubmitting = ref(false);
const selectedClient = ref<any>(null); const tokenName = ref(""); const oneTimeSecret = ref(""); const createFormRef = ref<FormInstance>();
const editingScopes = ref<string[]>([]);
const createForm = reactive({ client_name: "", client_code: "", service_user_id: "", scopes: [...scopeOptions] });
const rules = { client_name: [{ required: true, message: "请输入客户端名称", trigger: "blur" }], client_code: [{ required: true, pattern: /^[A-Za-z0-9_-]+$/, message: "仅支持字母、数字、下划线和短横线", trigger: "blur" }], service_user_id: [{ required: true, message: "请选择服务用户", trigger: "change" }] };
const mcpEndpoint = computed(() => `${window.location.protocol}//${window.location.hostname}:8001/mcp`);
const filteredCapabilities = computed(() => { const keyword = capabilityKeyword.value.trim().toLowerCase(); return capabilities.value.filter((item:any) => (!moduleFilter.value || item.module === moduleFilter.value) && (!keyword || `${item.name} ${item.description} ${item.scope}`.toLowerCase().includes(keyword))); });

async function loadClients() { loading.value = true; try { clients.value = await mcpManagementApi.clients() || []; } finally { loading.value = false; } }
async function loadUsers() { const res: any = await userApi.list({ page: 1, page_size: 100, status: "active" }); users.value = res.items || []; }
async function loadAudit() { auditLoading.value = true; try { toolCalls.value = await mcpManagementApi.toolCalls(200) || []; } finally { auditLoading.value = false; } }
async function loadCapabilities() { capabilityLoading.value = true; try { const result:any = await mcpManagementApi.capabilities(); capabilities.value = result.items || []; capabilityModules.value = result.modules || []; } finally { capabilityLoading.value = false; } }
function handleTabChange(name: any) { if (name === "audit") loadAudit(); if (name === "capabilities" && !capabilities.value.length) loadCapabilities(); if (name === "changes") changeSetCenterRef.value?.loadData(); }
function riskLabel(value:string) { return ({ low:"低", medium:"中", high:"高" } as any)[value] || value; }
function riskTag(value:string) { return value === "high" ? "danger" : value === "medium" ? "warning" : "success"; }
function openCreate() { Object.assign(createForm, { client_name: "", client_code: "", service_user_id: users.value[0]?.id || "", scopes: [...scopeOptions] }); createVisible.value = true; }
async function createClient() { if (!await createFormRef.value?.validate().catch(() => false)) return; submitting.value = true; try { await mcpManagementApi.createClient(createForm); ElMessage.success("客户端已创建"); createVisible.value = false; await loadClients(); } finally { submitting.value = false; } }
async function openTokens(client: any) { selectedClient.value = client; tokenVisible.value = true; tokenLoading.value = true; try { tokens.value = await mcpManagementApi.tokens(client.id) || []; } finally { tokenLoading.value = false; } }
function openScopes(client: any) { selectedClient.value = client; editingScopes.value = [...(client.scopes || [])]; scopeVisible.value = true; }
async function saveScopes() { scopeSubmitting.value = true; try { await mcpManagementApi.updateScopes(selectedClient.value.id, editingScopes.value); ElMessage.success("授权范围已更新"); scopeVisible.value = false; await loadClients(); } finally { scopeSubmitting.value = false; } }
async function issueToken() { if (!tokenName.value.trim()) return ElMessage.warning("请输入凭证名称"); tokenSubmitting.value = true; try { const data: any = await mcpManagementApi.issueToken(selectedClient.value.id, { token_name: tokenName.value.trim() }); oneTimeSecret.value = data.access_token; tokenCreateVisible.value = false; secretVisible.value = true; tokenName.value = ""; await openTokens(selectedClient.value); } finally { tokenSubmitting.value = false; } }
async function copySecret() { await navigator.clipboard.writeText(oneTimeSecret.value); ElMessage.success("Token 已复制"); }
function closeSecret() { oneTimeSecret.value = ""; secretVisible.value = false; }
async function revoke(row: any) { await ElMessageBox.confirm(`确认吊销凭证“${row.token_name}”？吊销后无法恢复。`, "吊销凭证", { type: "warning" }); await mcpManagementApi.revokeToken(selectedClient.value.id, row.id); ElMessage.success("凭证已吊销"); await openTokens(selectedClient.value); }
onMounted(async () => { await Promise.all([loadClients(), loadUsers()]); });
</script>

<style scoped lang="scss">
.mcp-page { padding: 4px; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:18px; h2 { margin:0 0 7px; font-size:20px; } p { margin:0; color:var(--el-text-color-secondary); font-size:13px; } }
.endpoint-alert { margin-bottom:18px; line-height:1.6; code { margin-left:4px; } }
.scope-tag { margin:2px 6px 2px 0; }
.token-toolbar { display:flex; justify-content:flex-end; margin-bottom:14px; }
.secret-box { display:flex; gap:10px; margin-top:18px; }
.scope-editor { display:grid; grid-template-columns:1fr 1fr; gap:8px 14px; }
.capability-toolbar { display:flex; align-items:center; gap:10px; margin-bottom:14px; }
.capability-total { color:var(--el-text-color-secondary); font-size:13px; }
.parameter-list { display:flex; flex-wrap:wrap; gap:5px; color:var(--el-text-color-secondary); }
</style>
