<template>
  <div class="development-page">
    <header class="page-heading">
      <div><h2>数据开发</h2><p>连接数据源编写与执行 SQL，统一管理开发脚本和查询结果。</p></div>
      <div class="heading-actions">
        <span class="shortcut"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> 执行</span>
        <el-button type="primary" :icon="Plus" @click="newScript()">新建脚本</el-button>
      </div>
    </header>

    <div class="development-shell">
      <aside class="script-sidebar">
        <div class="sidebar-title">
          <div><span>SQL 脚本</span><small>{{ scriptList.length }} 个</small></div>
          <el-tooltip content="新建脚本"><el-button circle text :icon="Plus" @click="newScript()" /></el-tooltip>
        </div>
        <el-input v-model="searchKeyword" placeholder="搜索脚本" :prefix-icon="Search" clearable class="script-search" @input="loadScripts" />
        <el-scrollbar class="script-list">
          <div v-for="script in scriptList" :key="script.id" class="script-item" :class="{ active: script.id === currentScriptId }" @click="loadScript(script)">
            <span class="script-file-icon"><el-icon><Document /></el-icon></span>
            <div class="script-info"><div class="script-name">{{ script.script_name }}</div><div class="script-meta">SQL 脚本</div></div>
            <el-button class="delete-button" circle text type="danger" :icon="Delete" @click.stop="deleteScript(script)" />
          </div>
          <el-empty v-if="!scriptLoading && scriptList.length === 0" description="暂无 SQL 脚本" :image-size="64" />
        </el-scrollbar>
      </aside>

      <main class="workbench-main">
        <section class="editor-card">
          <div class="editor-titlebar">
            <div class="script-identity">
              <span class="sql-mark">SQL</span>
              <el-input v-model="scriptName" placeholder="未命名脚本" class="name-input" @input="dirty = true" />
              <span class="save-state" :class="{ dirty }"><i></i>{{ currentScriptId ? (dirty ? "未保存" : "已保存") : "新脚本" }}</span>
            </div>
            <div class="editor-actions">
              <el-button :icon="DocumentAdd" @click="saveScript">保存</el-button>
              <el-button type="primary" :icon="VideoPlay" :loading="executing" @click="executeScript">执行</el-button>
            </div>
          </div>

          <div class="connection-bar">
            <div class="connection-summary"><el-icon><Connection /></el-icon><span>{{ selectedDatasourceName || "配置执行环境" }}</span><em v-if="currentDatabase">/ {{ currentDatabase }}</em></div>
            <label><span>数据源</span>
              <el-select v-model="currentDatasource" placeholder="选择数据源" filterable class="source-select" @change="onDatasourceChange">
                <el-option v-for="ds in sourceOptions" :key="ds.id" :label="ds.source_name" :value="ds.id" />
              </el-select>
            </label>
            <label><span>数据库 / Schema</span>
              <el-select v-model="currentDatabase" placeholder="选择数据库" clearable class="database-select">
                <el-option v-for="db in databases" :key="db.name" :label="db.name" :value="db.name" />
              </el-select>
            </label>
            <label><span>最大返回行数</span><el-input-number v-model="limit" :min="1" :max="100000" :step="1000" controls-position="right" /></label>
          </div>
          <div class="editor-body"><div ref="editorRef" class="sql-editor"></div></div>
        </section>

        <section class="result-card">
          <div class="result-titlebar">
            <div class="result-title"><span>查询结果</span><el-tag v-if="queryResult" type="success" effect="light" round>执行成功</el-tag></div>
            <div v-if="queryResult" class="result-stats">
              <span><strong>{{ queryResult.row_count }}</strong> 行</span><span>{{ queryResult.elapsed_ms }} ms</span>
              <span v-if="queryResult.truncated" class="truncated-warning">结果已截断</span>
            </div>
          </div>
          <div v-if="queryResult" class="result-table-wrap">
            <el-table :data="queryResult.rows" border size="small" height="100%">
              <el-table-column v-for="column in queryResult.columns" :key="column" :label="column" min-width="140" show-overflow-tooltip>
                <template #default="{ row }">{{ formatCell(row[column]) }}</template>
              </el-table-column>
            </el-table>
          </div>
          <div v-else class="result-placeholder">
            <span class="placeholder-icon"><el-icon><DataAnalysis /></el-icon></span>
            <div><strong>等待执行 SQL</strong><p>选择数据源并执行脚本后，查询结果将在这里展示。</p></div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Connection, DataAnalysis, Delete, Document, DocumentAdd, Plus, Search, VideoPlay } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { datasourceApi, etlScriptApi } from "@/api";
import CodeMirror from "codemirror";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/sql/sql";
import "codemirror/addon/edit/matchbrackets";
import "codemirror/addon/edit/closebrackets";
import "codemirror/theme/material-darker.css";

const DEFAULT_SQL = "-- 选择数据源与数据库后编写 SQL\nSELECT *\nFROM your_table\nLIMIT 100;";
const executing = ref(false), dirty = ref(false), limit = ref(10000), queryResult = ref<any>(null), searchKeyword = ref("");
const scriptLoading = ref(false), scriptList = ref<any[]>([]), currentScriptId = ref(""), scriptName = ref("");
const sourceOptions = ref<any[]>([]), currentDatasource = ref(""), currentDatabase = ref(""), databases = ref<any[]>([]);
const editorRef = ref<HTMLElement | null>(null);
let cmInstance: any = null;
let scriptContent = DEFAULT_SQL;

const selectedDatasourceName = computed(() => sourceOptions.value.find((item) => item.id === currentDatasource.value)?.source_name || "");

function setEditorContent(content: string) {
  scriptContent = content;
  if (cmInstance) cmInstance.setValue(content);
  dirty.value = false;
}
function formatCell(value: unknown) {
  if (value === null || value === undefined) return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
async function loadScripts() {
  scriptLoading.value = true;
  try {
    const res = await etlScriptApi.list({ page: 1, page_size: 100, language: "sql", keyword: searchKeyword.value || undefined });
    scriptList.value = res.items || [];
  } finally { scriptLoading.value = false; }
}
function newScript(showMessage = true) {
  currentScriptId.value = ""; scriptName.value = ""; setEditorContent(DEFAULT_SQL); queryResult.value = null;
  if (showMessage) ElMessage.success("已创建空白 SQL 脚本");
}
async function loadScript(script: any) {
  const detail = await etlScriptApi.detail(script.id);
  currentScriptId.value = detail.id; scriptName.value = detail.script_name; setEditorContent(detail.content || ""); queryResult.value = null;
}
async function saveScript() {
  if (!scriptName.value.trim()) return void ElMessage.warning("请输入脚本名称");
  scriptContent = cmInstance ? cmInstance.getValue() : scriptContent;
  const payload = { script_name: scriptName.value.trim(), language: "sql", content: scriptContent };
  if (currentScriptId.value) { await etlScriptApi.update(currentScriptId.value, payload); ElMessage.success("脚本已保存"); }
  else { const created = await etlScriptApi.create(payload); currentScriptId.value = created.id; ElMessage.success("脚本已创建"); }
  dirty.value = false; await loadScripts();
}
async function deleteScript(script: any) {
  await ElMessageBox.confirm(`确认删除脚本“${script.script_name}”？`, "删除确认", { type: "warning" });
  await etlScriptApi.delete(script.id);
  if (currentScriptId.value === script.id) newScript(false);
  await loadScripts(); ElMessage.success("脚本已删除");
}
async function executeScript() {
  if (!currentScriptId.value) return void ElMessage.warning("请先命名并保存脚本");
  if (!currentDatasource.value) return void ElMessage.warning("请选择数据源");
  executing.value = true;
  try {
    scriptContent = cmInstance ? cmInstance.getValue() : scriptContent;
    await etlScriptApi.update(currentScriptId.value, { script_name: scriptName.value.trim(), content: scriptContent });
    dirty.value = false;
    const res = await etlScriptApi.execute(currentScriptId.value, { limit: limit.value, datasource_id: currentDatasource.value, database: currentDatabase.value || null });
    queryResult.value = res; ElMessage.success(`查询成功，返回 ${res.row_count} 行`);
  } finally { executing.value = false; }
}
async function loadDatasources() {
  const res = await datasourceApi.list({ page: 1, page_size: 100, status: "active" });
  sourceOptions.value = res.items || [];
}
async function onDatasourceChange() {
  currentDatabase.value = ""; databases.value = [];
  const datasource = sourceOptions.value.find((item) => item.id === currentDatasource.value);
  const names: string[] = [];
  try { const res = await datasourceApi.listDatabases(currentDatasource.value); if (Array.isArray(res)) names.push(...res); } catch { /* 使用默认数据库 */ }
  const defaultDatabase = datasource?.database_name || "";
  if (defaultDatabase && !names.includes(defaultDatabase)) names.unshift(defaultDatabase);
  databases.value = names.map((name) => ({ name })); currentDatabase.value = defaultDatabase || names[0] || "";
}

onMounted(() => {
  if (editorRef.value) {
    cmInstance = CodeMirror(editorRef.value, { value: scriptContent, mode: "text/x-sql", theme: "material-darker", lineNumbers: true, matchBrackets: true, autoCloseBrackets: true, indentUnit: 2, extraKeys: { "Ctrl-Enter": executeScript } });
    cmInstance.on("change", (instance: any) => { scriptContent = instance.getValue(); dirty.value = true; });
  }
  Promise.all([loadScripts(), loadDatasources()]);
});
onBeforeUnmount(() => {
  const wrapper = cmInstance?.getWrapperElement?.();
  if (wrapper?.parentNode) wrapper.parentNode.removeChild(wrapper);
  cmInstance = null;
});
</script>

<style lang="scss" scoped>
.development-page { height: calc(100vh - 116px); min-height: 680px; display: flex; flex-direction: column; gap: 16px; color: #172033; }
.page-heading { display: flex; align-items: center; justify-content: space-between; flex: 0 0 auto; }
.page-heading h2 { margin: 0; font-size: 22px; line-height: 30px; }
.page-heading p { margin: 4px 0 0; color: #7a8498; font-size: 13px; }
.heading-actions, .script-identity, .editor-actions { display: flex; align-items: center; gap: 10px; }
.heading-actions { gap: 16px; }
.shortcut { display: flex; align-items: center; gap: 5px; color: #8992a5; font-size: 12px; }
.shortcut kbd { padding: 2px 6px; border: 1px solid #d9deea; border-radius: 5px; background: #fff; font: inherit; color: #5f687b; box-shadow: 0 1px 1px rgba(23,32,51,.06); }
.development-shell { min-height: 0; flex: 1; display: grid; grid-template-columns: 230px minmax(0,1fr); overflow: hidden; border: 1px solid #e4e8f0; border-radius: 12px; background: #fff; box-shadow: 0 8px 24px rgba(26,40,72,.05); }
.script-sidebar { min-width: 0; display: flex; flex-direction: column; border-right: 1px solid #e8ebf2; background: #fafbfc; }
.sidebar-title { height: 58px; padding: 0 14px 0 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e8ebf2; }
.sidebar-title > div { display: flex; align-items: baseline; gap: 8px; font-size: 14px; font-weight: 650; }
.sidebar-title small { color: #9aa3b4; font-size: 11px; font-weight: 400; }
.script-search { width: auto; margin: 12px; }
.script-list { flex: 1; min-height: 0; padding: 0 8px 12px; }
.script-item { display: flex; align-items: center; gap: 10px; min-height: 54px; padding: 7px 8px; margin-bottom: 4px; border: 1px solid transparent; border-radius: 8px; cursor: pointer; transition: all .16s ease; }
.script-item:hover { background: #f1f4f9; }
.script-item.active { border-color: #cfe0ff; background: #edf4ff; }
.script-file-icon { width: 30px; height: 30px; display: grid; place-items: center; flex: 0 0 auto; border-radius: 7px; color: #377cf6; background: #e7f0ff; }
.script-info { min-width: 0; flex: 1; }
.script-name { overflow: hidden; color: #30394c; font-size: 13px; font-weight: 550; text-overflow: ellipsis; white-space: nowrap; }
.script-meta { margin-top: 3px; color: #a0a8b8; font-size: 11px; }
.delete-button { opacity: 0; transition: opacity .16s; }
.script-item:hover .delete-button { opacity: 1; }
.workbench-main { min-width: 0; min-height: 0; display: grid; grid-template-rows: minmax(380px,3fr) minmax(220px,2fr); }
.editor-card { min-height: 0; display: flex; flex-direction: column; border-bottom: 1px solid #e4e8f0; }
.editor-titlebar { min-height: 58px; padding: 0 16px; display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid #e8ebf2; }
.script-identity { min-width: 0; flex: 1; }
.sql-mark { padding: 4px 6px; border-radius: 5px; color: #2267dc; background: #e8f1ff; font-size: 10px; font-weight: 750; letter-spacing: .5px; }
.name-input { max-width: 360px; }
.name-input :deep(.el-input__wrapper) { padding-left: 2px; box-shadow: none; background: transparent; }
.name-input :deep(.el-input__inner) { color: #202a3e; font-size: 15px; font-weight: 600; }
.save-state { display: inline-flex; align-items: center; gap: 5px; color: #8b94a6; font-size: 11px; white-space: nowrap; }
.save-state i { width: 6px; height: 6px; border-radius: 50%; background: #52c27d; }
.save-state.dirty i { background: #f2a93b; }
.connection-bar { min-height: 66px; padding: 8px 16px; display: flex; align-items: flex-end; gap: 12px; background: #f8f9fb; border-bottom: 1px solid #e8ebf2; }
.connection-summary { height: 32px; min-width: 165px; display: flex; align-items: center; gap: 6px; color: #526075; font-size: 12px; }
.connection-summary .el-icon { color: #377cf6; font-size: 16px; }
.connection-summary em { overflow: hidden; max-width: 110px; color: #919aac; font-style: normal; text-overflow: ellipsis; white-space: nowrap; }
.connection-bar label { display: flex; flex-direction: column; gap: 4px; color: #7d8799; font-size: 11px; }
.source-select { width: 180px; } .database-select { width: 160px; }
.connection-bar :deep(.el-input-number) { width: 132px; }
.editor-body { min-height: 0; flex: 1; padding: 10px; background: #1e2430; }
.sql-editor { height: 100%; min-height: 200px; }
.sql-editor :deep(.CodeMirror) { height: 100%; background: #1e2430; font-family: "JetBrains Mono","Fira Code",Consolas,monospace; font-size: 13px; line-height: 1.65; }
.sql-editor :deep(.CodeMirror-gutters) { border-right-color: #303848; background: #1e2430; }
.result-card { min-height: 0; display: flex; flex-direction: column; background: #fff; }
.result-titlebar { min-height: 48px; padding: 0 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e8ebf2; }
.result-title { display: flex; align-items: center; gap: 10px; color: #30394c; font-size: 13px; font-weight: 650; }
.result-title :deep(.el-tag) { height: 21px; font-size: 10px; }
.result-stats { display: flex; align-items: center; gap: 18px; color: #818a9c; font-size: 12px; }
.result-stats strong { color: #3c465a; font-weight: 650; }
.truncated-warning { color: #d99022; }
.result-table-wrap { min-height: 0; flex: 1; padding: 10px 12px 12px; }
.result-placeholder { min-height: 0; flex: 1; display: flex; align-items: center; justify-content: center; gap: 14px; color: #8c95a7; }
.placeholder-icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 12px; color: #6f9ff4; background: #eef4ff; font-size: 25px; }
.result-placeholder strong { color: #515b6f; font-size: 13px; }
.result-placeholder p { margin: 5px 0 0; font-size: 12px; }
@media (max-width: 1180px) { .development-shell { grid-template-columns: 200px minmax(0,1fr); } .connection-summary { display: none; } }
@media (max-width: 900px) { .development-page { height: auto; min-height: 760px; } .development-shell { grid-template-columns: 1fr; grid-template-rows: 200px minmax(0,1fr); } .script-sidebar { border-right: 0; border-bottom: 1px solid #e8ebf2; } .connection-bar { flex-wrap: wrap; } .shortcut { display: none; } }
</style>
