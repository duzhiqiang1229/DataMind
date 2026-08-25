<template>
  <div class="quality-page">
    <el-card shadow="never">
      <template #header>
        <div class="header">
          <div><div class="title">数据质量</div><div class="subtitle">配置并手动执行表级、字段级质量检查</div></div>
          <el-button type="primary" :icon="Plus" @click="openDialog">新建规则</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="rules" border stripe>
        <el-table-column prop="rule_name" label="规则名称" min-width="160" />
        <el-table-column prop="asset_name" label="资产" min-width="180"><template #default="{ row }"><div>{{ row.asset_name }}</div><div class="fqn">{{ row.asset_fqn }}</div></template></el-table-column>
        <el-table-column prop="column_name" label="字段" min-width="130"><template #default="{ row }">{{ row.column_name || '整表' }}</template></el-table-column>
        <el-table-column prop="rule_type" label="规则类型" width="120"><template #default="{ row }">{{ ruleTypeLabel(row.rule_type) }}</template></el-table-column>
        <el-table-column label="最近结果" width="140"><template #default="{ row }"><el-tag v-if="row.last_run" :type="row.last_run.status === 'passed' ? 'success' : 'danger'">{{ row.last_run.status === 'passed' ? '通过' : '失败' }}</el-tag><span v-else>-</span></template></el-table-column>
        <el-table-column label="通过率" width="100" align="right"><template #default="{ row }">{{ row.last_run ? `${row.last_run.pass_rate.toFixed(2)}%` : '-' }}</template></el-table-column>
        <el-table-column label="异常数" width="90" align="right"><template #default="{ row }">{{ row.last_run?.failed_count ?? '-' }}</template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button link type="primary" :loading="runningId === row.id" @click="runRule(row)">执行</el-button><el-button link type="danger" @click="removeRule(row)">删除</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!loading && !rules.length" description="暂无质量规则" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建质量规则" width="640px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="规则名称" required><el-input v-model="form.rule_name" placeholder="如：客户名称非空" /></el-form-item>
        <el-form-item label="数据资产" required><el-select v-model="form.asset_id" filterable style="width: 100%" placeholder="选择表" @change="loadAssetColumns"><el-option v-for="asset in assets" :key="asset.id" :label="asset.fqn" :value="asset.id" /></el-select></el-form-item>
        <el-form-item label="规则类型" required><el-select v-model="form.rule_type" style="width: 100%" @change="onRuleTypeChange"><el-option label="非空检查" value="not_null" /><el-option label="唯一性检查" value="unique" /><el-option label="数值范围" value="range" /><el-option label="自定义 SQL" value="custom_sql" /></el-select></el-form-item>
        <el-form-item v-if="form.rule_type !== 'custom_sql'" label="检查字段" required><el-select v-model="form.column_name" filterable style="width: 100%"><el-option v-for="column in columns" :key="column.name" :label="`${column.name} (${column.data_type})`" :value="column.name" /></el-select></el-form-item>
        <template v-if="form.rule_type === 'range'"><el-form-item label="最小值" required><el-input-number v-model="form.config.min" style="width: 100%" /></el-form-item><el-form-item label="最大值" required><el-input-number v-model="form.config.max" style="width: 100%" /></el-form-item></template>
        <el-form-item v-if="form.rule_type === 'custom_sql'" label="异常 SQL" required><el-input v-model="form.config.sql" type="textarea" :rows="5" placeholder="输入只读 SQL；每一条返回记录视为异常" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveRule">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { dataAssetApi } from "@/api";

const loading = ref(false), saving = ref(false), dialogVisible = ref(false), runningId = ref("");
const rules = ref<any[]>([]), assets = ref<any[]>([]), columns = ref<any[]>([]);
const form = reactive<any>({ asset_id: "", rule_name: "", rule_type: "not_null", column_name: "", config: {} });
async function loadRules() { loading.value = true; try { rules.value = await dataAssetApi.qualityRules() as any[]; } finally { loading.value = false; } }
async function loadAssets() { const res: any = await dataAssetApi.catalog({ page: 1, page_size: 100 }); assets.value = res.items || []; }
async function loadAssetColumns() { form.column_name = ""; if (!form.asset_id) { columns.value = []; return; } const detail: any = await dataAssetApi.detail(form.asset_id); columns.value = detail.columns || []; }
function openDialog() { Object.assign(form, { asset_id: "", rule_name: "", rule_type: "not_null", column_name: "", config: {} }); columns.value = []; dialogVisible.value = true; loadAssets(); }
function onRuleTypeChange() { form.column_name = ""; form.config = {}; }
async function saveRule() { if (!form.asset_id || !form.rule_name || (form.rule_type !== "custom_sql" && !form.column_name)) { ElMessage.warning("请填写完整规则配置"); return; } saving.value = true; try { await dataAssetApi.createQualityRule({ ...form, config: { ...form.config } }); ElMessage.success("质量规则已创建"); dialogVisible.value = false; await loadRules(); } finally { saving.value = false; } }
async function runRule(row: any) { runningId.value = row.id; try { const result: any = await dataAssetApi.runQualityRule(row.id); ElMessage[result.status === "passed" ? "success" : "warning"](`执行完成：异常 ${result.failed_count} 条，通过率 ${result.pass_rate.toFixed(2)}%`); await loadRules(); } finally { runningId.value = ""; } }
async function removeRule(row: any) { await ElMessageBox.confirm(`确认删除质量规则“${row.rule_name}”？`, "删除确认", { type: "warning" }); await dataAssetApi.deleteQualityRule(row.id); ElMessage.success("已删除"); await loadRules(); }
function ruleTypeLabel(value: string) { return ({ not_null: "非空检查", unique: "唯一性检查", range: "数值范围", custom_sql: "自定义 SQL" } as any)[value] || value; }
onMounted(loadRules);
</script>

<style scoped lang="scss">
.quality-page { padding: 16px; }.header { display: flex; justify-content: space-between; align-items: center; }.title { font-size: 18px; font-weight: 600; }.subtitle, .fqn { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 5px; }
</style>
