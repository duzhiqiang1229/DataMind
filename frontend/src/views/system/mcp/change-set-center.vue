<template>
  <div class="change-center">
    <div class="toolbar">
      <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width:150px" @change="loadData">
        <el-option label="草稿" value="draft" /><el-option label="已提交" value="committed" /><el-option label="已废弃" value="discarded" />
      </el-select>
      <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      <span class="tip">Agent 的所有写操作先进入这里，确认后才写入业务对象。</span>
    </div>
    <el-table v-loading="loading" :data="items" border @row-dblclick="openDetail">
      <el-table-column prop="change_set_code" label="变更集编码" min-width="205" />
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column label="MCP客户端" min-width="160"><template #default="{ row }">{{ row.client_name }}<div class="muted">{{ row.client_code }}</div></template></el-table-column>
      <el-table-column prop="item_count" label="变更项" width="85" align="center" />
      <el-table-column label="校验" width="100"><template #default="{ row }"><el-tag :type="validationTag(row.validation_status)">{{ validationLabel(row.validation_status) }}</el-tag></template></el-table-column>
      <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
      <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="90" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">查看</el-button></template></el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无 MCP 变更集" />

    <el-drawer v-model="drawerVisible" title="变更集详情" size="760px" destroy-on-close>
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="编码">{{ detail.change_set_code }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="statusTag(detail.status)">{{ statusLabel(detail.status) }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="标题" :span="2">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="客户端">{{ detail.client_name }}</el-descriptions-item>
          <el-descriptions-item label="校验"><el-tag :type="validationTag(detail.validation_status)">{{ validationLabel(detail.validation_status) }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="说明" :span="2">{{ detail.description || "-" }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="validationErrors.length || validationWarnings.length" class="validation-box">
          <el-alert v-if="validationErrors.length" type="error" :closable="false" show-icon :title="`校验失败：${validationErrors.length}项错误`">
            <div v-for="(error, index) in validationErrors" :key="index">{{ index + 1 }}. {{ error.message }}</div>
          </el-alert>
          <el-alert v-if="validationWarnings.length" type="warning" :closable="false" show-icon :title="`校验警告：${validationWarnings.length}项`">
            <div v-for="(warning, index) in validationWarnings" :key="index">{{ index + 1 }}. {{ warning.message }}</div>
          </el-alert>
        </div>

        <h3 class="section-title">变更内容</h3>
        <el-collapse>
          <el-collapse-item v-for="(item, index) in detail.items" :key="item.id" :name="item.id">
            <template #title><span class="item-title"><el-tag size="small">新增</el-tag><strong>{{ objectTypeLabel(item.object_type) }}</strong><span>{{ objectName(item) }}</span><el-tag v-if="item.validation_result?.passed === false" size="small" type="danger">有错误</el-tag></span></template>
            <div class="diff-grid">
              <div class="diff-side before"><div class="diff-title">提交前</div><div class="empty-state">对象不存在</div></div>
              <div class="diff-side after"><div class="diff-title">提交后</div><pre>{{ prettyPayload(item.payload) }}</pre></div>
            </div>
            <el-alert v-if="item.validation_result?.errors?.length" type="error" :closable="false" :title="item.validation_result.errors.join('；')" />
          </el-collapse-item>
        </el-collapse>
      </template>
      <template #footer v-if="detail?.status === 'draft'">
        <div class="drawer-footer">
          <el-button type="danger" plain :loading="actionLoading" @click="discard">废弃</el-button>
          <div><el-button :loading="actionLoading" @click="validate">重新校验</el-button><el-button type="primary" :disabled="detail.validation_status !== 'passed'" :loading="actionLoading" @click="commit">确认提交</el-button></div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { mcpManagementApi } from "@/api";
import { formatDateTime } from "@/utils/format";

const loading = ref(false); const actionLoading = ref(false); const items = ref<any[]>([]); const statusFilter = ref("");
const drawerVisible = ref(false); const detail = ref<any>(null);
const validationErrors = computed(() => detail.value?.validation_result?.errors || []);
const validationWarnings = computed(() => detail.value?.validation_result?.warnings || []);
const objectLabels: Record<string,string> = { data_domain:"数据域", business_process:"业务过程", data_model:"数据模型", sql_script:"SQL脚本", metric_category:"指标分类", cube_model:"Cube模型", metric_definition:"指标定义", airflow_sql_dag:"Airflow SQL任务", data_service_api:"数据API", quality_rule:"质量规则" };
function objectTypeLabel(type:string){ return objectLabels[type] || type; }
function objectName(item:any){ const p=item.payload||{}; return p.domain_name||p.process_name||p.model_name||p.script_name||p.category_name||p.title||p.metric_name||p.api_name||p.rule_name||p.name||""; }
function prettyPayload(payload:any){ return JSON.stringify(payload||{}, null, 2); }
function statusLabel(value:string){ return ({draft:"草稿",committed:"已提交",discarded:"已废弃"} as any)[value]||value; }
function statusTag(value:string){ return value==="committed"?"success":value==="discarded"?"info":"warning"; }
function validationLabel(value:string){ return ({pending:"待校验",passed:"通过",failed:"失败"} as any)[value]||value; }
function validationTag(value:string){ return value==="passed"?"success":value==="failed"?"danger":"info"; }
async function loadData(){ loading.value=true; try{ items.value=await mcpManagementApi.changeSets(statusFilter.value)||[]; }finally{ loading.value=false; } }
async function openDetail(row:any){ drawerVisible.value=true; detail.value=await mcpManagementApi.changeSetDetail(row.id); }
async function refreshDetail(){ if(detail.value) detail.value=await mcpManagementApi.changeSetDetail(detail.value.id); await loadData(); }
async function validate(){ actionLoading.value=true; try{ const result:any=await mcpManagementApi.validateChangeSet(detail.value.id); ElMessage[result.passed?"success":"error"](result.passed?"变更集校验通过":"变更集校验未通过"); await refreshDetail(); }finally{ actionLoading.value=false; } }
async function commit(){ await ElMessageBox.confirm("确认将该变更集写入 DataMind？SQL不会自动执行，Doris DDL不会自动执行；Cube需要单独刷新，Airflow任务默认保持暂停，数据API保持草稿，质量规则不会自动运行。", "确认提交", {type:"warning",confirmButtonText:"确认提交"}); actionLoading.value=true; try{ const result:any=await mcpManagementApi.commitChangeSet(detail.value.id); const pending:string[]=[]; if(result.cube_refresh_required) pending.push("Cube需要刷新"); if(result.airflow_activation_required) pending.push("Airflow任务需要确认启用"); if(result.data_services_pending_publish?.length) pending.push("数据API需要确认发布"); if(result.quality_rules_pending_execution?.length) pending.push("质量规则需要确认执行"); ElMessage.success(pending.length?`已提交；${pending.join("，")}`:"变更集已提交"); await refreshDetail(); }finally{ actionLoading.value=false; } }
async function discard(){ await ElMessageBox.confirm("确认废弃该草稿变更集？业务对象不会发生变化。", "废弃变更集", {type:"warning",confirmButtonText:"确认废弃"}); actionLoading.value=true; try{ await mcpManagementApi.discardChangeSet(detail.value.id); ElMessage.success("变更集已废弃"); await refreshDetail(); }finally{ actionLoading.value=false; } }
onMounted(loadData);
defineExpose({loadData});
</script>

<style scoped lang="scss">
.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:14px}.tip,.muted{color:var(--el-text-color-secondary);font-size:12px}.validation-box{display:grid;gap:10px;margin-top:16px}.section-title{font-size:15px;margin:22px 0 12px}.item-title{display:flex;align-items:center;gap:9px}.diff-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.diff-side{border:1px solid var(--el-border-color);border-radius:6px;overflow:hidden}.diff-title{padding:8px 12px;background:var(--el-fill-color-light);font-weight:600}.diff-side pre{margin:0;padding:12px;max-height:360px;overflow:auto;white-space:pre-wrap;word-break:break-all;font-size:12px}.empty-state{padding:30px 12px;text-align:center;color:var(--el-text-color-placeholder)}.after{border-color:var(--el-color-success-light-5)}.drawer-footer{width:100%;display:flex;justify-content:space-between}
</style>
