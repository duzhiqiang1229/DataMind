<template>
  <div class="etl-workbench">
    <el-row :gutter="12" class="workbench-row">
      <!-- 脚本库 -->
      <el-col :span="6" style="height: 100%;">
        <div class="panel script-panel">
          <div class="panel-header">
            <span class="panel-title">脚本库</span>
            <el-button type="primary" size="small" :icon="Plus" @click="newScript">新建</el-button>
          </div>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索脚本名称"
            :prefix-icon="Search"
            clearable
            size="small"
            class="script-search"
            @input="loadScripts"
          />
          <el-scrollbar class="script-list">
            <div
              v-for="s in scriptList"
              :key="s.id"
              class="script-item"
              :class="{ active: s.id === currentScriptId }"
              @click="loadScript(s)"
            >
              <el-icon class="script-icon"><Document /></el-icon>
              <div class="script-info">
                <div class="script-name">
                  {{ s.script_name }}<span class="script-ext">.sql</span>
                </div>
                <div class="script-meta">
                  <el-button link type="danger" size="small" class="delete-btn" @click.stop="deleteScript(s)">删除</el-button>
                </div>
              </div>
            </div>
            <el-empty v-if="!scriptLoading && scriptList.length === 0" description="暂无脚本" :image-size="50" />
          </el-scrollbar>
        </div>
      </el-col>

      <!-- SQL 编辑器 -->
      <el-col :span="18" style="height: 100%;">
        <div class="panel editor-panel">
          <div class="editor-toolbar">
            <el-input v-model="scriptName" placeholder="脚本名称" clearable size="small" class="name-input" />
            <el-divider direction="vertical" />
            <el-select v-model="currentDatasource" placeholder="数据源" filterable size="small" style="width: 170px;" @change="onDatasourceChange">
              <el-option v-for="ds in sourceOptions" :key="ds.id" :label="ds.source_name" :value="ds.id" />
            </el-select>
            <el-select v-model="currentDatabase" placeholder="数据库" clearable size="small" style="width: 120px;">
              <el-option v-for="db in databases" :key="db.name" :label="db.name" :value="db.name" />
            </el-select>
            <span class="limit-label">行数</span>
            <el-input-number v-model="limit" :min="1" :max="100000" :step="1000" size="small" style="width: 110px;" />
            <div class="toolbar-spacer" />
            <el-button type="primary" size="small" :icon="VideoPlay" :loading="executing" @click="executeScript">执行</el-button>
            <el-button type="primary" plain size="small" :icon="DocumentAdd" @click="saveScript">保存</el-button>
          </div>

          <div class="editor-body">
            <div ref="editorRef" class="sql-editor"></div>
          </div>

          <div v-if="queryResult" class="result-panel">
            <div class="result-header">
              <span>查询结果</span>
              <span class="result-info">
                返回 {{ queryResult.row_count }} 行
                <span v-if="queryResult.truncated" class="truncated-warning">(已截断)</span>
                · 耗时 {{ queryResult.elapsed_ms }}ms
              </span>
            </div>
            <el-table v-if="queryResult.columns" :data="queryResult.rows" border size="small" :max-height="320">
              <el-table-column
                v-for="col in queryResult.columns"
                :key="col"
                :prop="col"
                :label="col"
                min-width="120"
                show-overflow-tooltip
              />
            </el-table>
          </div>
          <div v-else class="result-placeholder">
            <el-icon><DataAnalysis /></el-icon>
            <span>保存脚本后点击「执行」查看查询结果</span>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { Plus, Search, VideoPlay, Document, DocumentAdd, DataAnalysis } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { datasourceApi, etlScriptApi } from "@/api";
import CodeMirror from "codemirror";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/sql/sql";
import "codemirror/addon/edit/matchbrackets";
import "codemirror/addon/edit/closebrackets";
import "codemirror/theme/material-darker.css";

const executing = ref(false);
const limit = ref(10000);
const queryResult = ref<any>(null);
const searchKeyword = ref("");

// script list
const scriptLoading = ref(false);
const scriptList = ref<any[]>([]);
const currentScriptId = ref("");
const scriptName = ref("");

// datasource
const sourceOptions = ref<any[]>([]);
const currentDatasource = ref("");
const currentDatabase = ref("");
const databases = ref<any[]>([]);

// CodeMirror
const editorRef = ref<HTMLElement | null>(null);
let cmInstance: any = null;
let scriptContent = "SELECT * FROM test.user_login_log LIMIT 100;";

async function loadScripts() {
  scriptLoading.value = true;
  try {
    const res = await etlScriptApi.list({
      page: 1,
      page_size: 100,
      language: "sql",
      keyword: searchKeyword.value || undefined,
    });
    scriptList.value = res.items || [];
  } catch {
    // handled
  } finally {
    scriptLoading.value = false;
  }
}

async function newScript() {
  currentScriptId.value = "";
  scriptName.value = "";
  scriptContent = "SELECT * FROM test.user_login_log LIMIT 100;";
  if (cmInstance) {
    cmInstance.setValue(scriptContent);
  }
  queryResult.value = null;
  ElMessage.success("已新建 SQL 脚本，请输入脚本名称并保存");
}

async function loadScript(s: any) {
  try {
    const detail = await etlScriptApi.detail(s.id);
    currentScriptId.value = detail.id;
    scriptName.value = detail.script_name;
    scriptContent = detail.content || "";
    if (cmInstance) {
      cmInstance.setValue(scriptContent);
    }
    queryResult.value = null;
  } catch {
    // handled
  }
}

async function saveScript() {
  if (!scriptName.value.trim()) {
    ElMessage.warning("请输入脚本名称");
    return;
  }
  scriptContent = cmInstance ? cmInstance.getValue() : scriptContent;
  try {
    const payload = {
      script_name: scriptName.value,
      language: "sql",
      content: scriptContent,
    };
    if (currentScriptId.value) {
      await etlScriptApi.update(currentScriptId.value, payload);
      ElMessage.success("脚本已更新");
    } else {
      const created = await etlScriptApi.create(payload);
      currentScriptId.value = created.id;
      ElMessage.success("脚本已保存");
    }
    loadScripts();
  } catch {
    // handled
  }
}

async function deleteScript(s: any) {
  await ElMessageBox.confirm(`确认删除脚本 "${s.script_name}"？`, "删除确认", { type: "warning" });
  try {
    await etlScriptApi.delete(s.id);
    ElMessage.success("删除成功");
    if (currentScriptId.value === s.id) {
      currentScriptId.value = "";
      newScript();
    }
    loadScripts();
  } catch {
    // handled
  }
}

async function executeScript() {
  if (!currentScriptId.value) {
    ElMessage.warning("请先保存脚本");
    return;
  }
  // persist latest content before execution
  scriptContent = cmInstance ? cmInstance.getValue() : scriptContent;
  await etlScriptApi.update(currentScriptId.value, { content: scriptContent });

  if (!currentDatasource.value) {
    ElMessage.warning("请选择数据源");
    return;
  }
  executing.value = true;
  try {
    const params: any = {
      limit: limit.value,
      datasource_id: currentDatasource.value,
      database: currentDatabase.value || null,
    };
    const res = await etlScriptApi.execute(currentScriptId.value, params);
    queryResult.value = res;
    ElMessage.success(`查询成功，返回 ${res.row_count} 行`);
  } catch {
    // handled
  } finally {
    executing.value = false;
  }
}

async function loadDatasources() {
  try {
    const res = await datasourceApi.list({ page: 1, page_size: 100, status: "active" });
    sourceOptions.value = res.items || [];
  } catch {
    sourceOptions.value = [];
  }
}

async function onDatasourceChange() {
  const ds = sourceOptions.value.find((d) => d.id === currentDatasource.value);
  const names: string[] = [];
  try {
    const res = await datasourceApi.listDatabases(currentDatasource.value);
    if (Array.isArray(res)) names.push(...res);
  } catch {
    // fallback to default database below
  }
  const defaultDb = ds?.database_name || "";
  if (defaultDb && !names.includes(defaultDb)) {
    names.unshift(defaultDb);
  }
  databases.value = names.map((name) => ({ name }));
  currentDatabase.value = defaultDb || names[0] || "";
}

onMounted(() => {
  if (editorRef.value) {
    cmInstance = CodeMirror(editorRef.value, {
      value: scriptContent,
      mode: "text/x-sql",
      theme: "material-darker",
      lineNumbers: true,
      matchBrackets: true,
      autoCloseBrackets: true,
      extraKeys: {
        "Ctrl-Enter": () => {
          executeScript();
        },
      },
    });
    cmInstance.on("change", (instance: any) => {
      scriptContent = instance.getValue();
    });
  }
  loadScripts();
  loadDatasources();
});

onBeforeUnmount(() => {
  if (cmInstance) {
    try {
      const wrapper = (cmInstance as any).getWrapperElement?.();
      if (wrapper && wrapper.parentNode) {
        wrapper.parentNode.removeChild(wrapper);
      }
    } catch {
      // ignore
    }
    cmInstance = null;
  }
});
</script>

<style lang="scss" scoped>
.etl-workbench {
  height: calc(100vh - 150px);
}

.workbench-row {
  height: 100%;
}

.panel {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-lighter);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.script-panel {
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  .panel-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.script-search {
  padding: 10px 12px 4px;
}

.script-list {
  flex: 1;
  padding: 6px 8px 10px;
}

.script-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  border-left: 3px solid transparent;
  transition: background-color 0.15s;

  &:hover {
    background: var(--el-fill-color-light);
  }

  &.active {
    background: var(--el-color-primary-light-9);
    border-left-color: var(--el-color-primary);
  }

  .script-icon {
    margin-top: 2px;
    color: var(--el-color-primary);
    font-size: 16px;
  }

  .script-info {
    flex: 1;
    min-width: 0;
  }

  .script-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;

    .script-ext {
      font-size: 12px;
      font-weight: normal;
      color: var(--el-text-color-secondary);
    }
  }

  .script-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 2px;

    .delete-btn {
      visibility: hidden;
    }
  }

  &:hover .delete-btn {
    visibility: visible;
  }
}

.editor-panel {
  height: 100%;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-wrap: wrap;

  .name-input {
    width: 200px;
  }

  .limit-label {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    white-space: nowrap;
  }

  .toolbar-spacer {
    flex: 1;
  }
}

.editor-body {
  flex: 1;
  min-height: 320px;
  padding: 10px;
  background: #1e1e1e;
}

.sql-editor {
  height: 100%;
  min-height: 300px;

  :deep(.CodeMirror) {
    height: 100%;
    font-family: "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 14px;
  }
}

.result-panel {
  border-top: 1px solid var(--el-border-color-lighter);

  .result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-primary);

    .result-info {
      font-weight: normal;
      color: var(--el-text-color-secondary);
    }

    .truncated-warning {
      color: var(--el-color-warning);
    }
  }
}

.result-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;

  .el-icon {
    font-size: 36px;
    color: var(--el-border-color);
  }
}
</style>
