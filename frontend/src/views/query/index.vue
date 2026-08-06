<template>
  <div class="query-workbench">
    <el-row :gutter="16">
      <!-- 左侧: 库表浏览 -->
      <el-col :span="6">
        <el-card class="schema-browser" shadow="never">
          <template #header>库表浏览</template>
          <el-input v-model="searchKeyword" placeholder="搜索表名" :prefix-icon="Search" clearable size="small" style="margin-bottom: 8px;" />
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ label: 'name', children: 'children' }"
            node-key="name"
            @node-click="handleNodeClick"
            :filter-node-method="filterNode"
          />
        </el-card>
      </el-col>

      <!-- 右侧: SQL 编辑器 + 结果 -->
      <el-col :span="18">
        <el-card shadow="never">
          <div class="sql-toolbar">
            <el-select v-model="currentDatabase" placeholder="选择数据库" size="small" style="width: 150px;" @change="onDatabaseChange">
              <el-option v-for="db in databases" :key="db.name" :label="db.name" :value="db.name" />
            </el-select>
            <el-input-number v-model="limit" :min="1" :max="100000" :step="1000" size="small" style="width: 130px;" />
            <el-button type="primary" size="small" :icon="VideoPlay" @click="executeQuery" :loading="executing">
              执行
            </el-button>
            <el-button size="small" :icon="Document" @click="openSaveDialog">保存查询</el-button>
            <el-button size="small" :icon="Clock" @click="openHistoryDialog">历史</el-button>
          </div>

          <!-- SQL Editor (CodeMirror) -->
          <div ref="editorRef" class="sql-editor"></div>

          <!-- Results -->
          <div v-if="queryResult" class="query-result">
            <div class="result-info">
              <span>返回 {{ queryResult.row_count }} 行</span>
              <span v-if="queryResult.truncated" class="truncated-warning">(已截断)</span>
              <span>耗时 {{ queryResult.elapsed_ms }}ms</span>
            </div>
            <el-table :data="queryResult.rows" border size="small" :max-height="400">
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
        </el-card>
      </el-col>
    </el-row>

    <!-- 保存查询对话框 -->
    <el-dialog v-model="saveDialogVisible" title="保存查询" width="500px">
      <el-form :model="saveForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="saveForm.query_name" placeholder="查询名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="saveForm.description" type="textarea" :rows="2" placeholder="查询描述" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="saveForm.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveQuery">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查询历史对话框 -->
    <el-dialog v-model="historyDialogVisible" title="查询历史" width="800px">
      <el-table :data="historyData" border size="small">
        <el-table-column prop="sql_text" label="SQL" show-overflow-tooltip min-width="200" />
        <el-table-column prop="database" label="数据库" width="100" />
        <el-table-column prop="row_count" label="行数" width="80" />
        <el-table-column prop="elapsed_ms" label="耗时(ms)" width="100" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executed_at" label="执行时间" width="180" />
      </el-table>
      <el-pagination
        v-model:current-page="historyPagination.page"
        :total="historyPagination.total"
        :page-size="20"
        layout="total, prev, pager, next"
        @current-change="loadHistory"
        style="margin-top: 12px; justify-content: flex-end;"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, reactive } from "vue";
import { Search, VideoPlay, Document, Clock } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { queryApi } from "@/api";
import CodeMirror from "codemirror";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/sql/sql";
import "codemirror/addon/hint/show-hint";
import "codemirror/addon/hint/sql-hint";
import "codemirror/addon/edit/matchbrackets";
import "codemirror/addon/edit/closebrackets";
import "codemirror/theme/material-darker.css";
// CodeMirror type declarations not available; using any

interface TreeNode {
  name: string;
  children?: TreeNode[];
}

interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  truncated: boolean;
  elapsed_ms: number;
}

const treeRef = ref();
const searchKeyword = ref("");
const databases = ref<TreeNode[]>([]);
const currentDatabase = ref("");
const sqlText = ref("SELECT * FROM ods.ods_user LIMIT 100;");
const limit = ref(10000);
const executing = ref(false);
const queryResult = ref<QueryResult | null>(null);
const treeData = ref<TreeNode[]>([]);

// CodeMirror
const editorRef = ref<HTMLElement | null>(null);
let cmInstance: any = null;

const saveDialogVisible = ref(false);
const saveForm = reactive({
  query_name: "",
  description: "",
  tags: "",
});

const historyDialogVisible = ref(false);
const historyData = ref<any[]>([]);
const historyPagination = reactive({ page: 1, total: 0 });

watch(searchKeyword, (val) => {
  treeRef.value?.filter(val);
});

// Update CodeMirror hint tables when currentDatabase changes
watch(currentDatabase, async (db) => {
  if (!db) return;
  await loadTables(db);
  if (cmInstance) {
    const tables: Record<string, string[]> = {};
    for (const node of treeData.value) {
      if (node.children) {
        for (const child of node.children) {
          tables[child.name] = [];
        }
      } else {
        tables[node.name] = [];
      }
    }
    cmInstance.setOption("hintOptions", { tables });
  }
});

onMounted(async () => {
  // Initialize CodeMirror
  if (editorRef.value) {
    const tables: Record<string, string[]> = {};
    cmInstance = CodeMirror(editorRef.value, {
      value: sqlText.value,
      mode: "text/x-sql",
      theme: "material-darker",
      lineNumbers: true,
      matchBrackets: true,
      autoCloseBrackets: true,
      hintOptions: { tables },
      extraKeys: {
        "Ctrl-Space": "autocomplete",
        "Ctrl-Enter": () => {
          executeQuery();
        },
      },
    });

    // Sync CodeMirror changes back to sqlText
    cmInstance.on("change", (instance: any) => {
      sqlText.value = instance.getValue();
    });
  }

  try {
    const res = await queryApi.listDatabases();
    databases.value = (res || []).map((name: any) => ({ name: typeof name === "string" ? name : name.name }));
    if (databases.value.length > 0) {
      currentDatabase.value = databases.value[0].name;
      await loadTables(currentDatabase.value);
      // Populate hint tables after initial load
      if (cmInstance) {
        const hintTables: Record<string, string[]> = {};
        for (const node of treeData.value) {
          if (node.children) {
            for (const child of node.children) {
              hintTables[child.name] = [];
            }
          } else {
            hintTables[node.name] = [];
          }
        }
        cmInstance.setOption("hintOptions", { tables: hintTables });
      }
    }
  } catch {
    // API not ready
  }
});

onBeforeUnmount(() => {
  if (cmInstance) {
    // Wrap in try/catch since some CodeMirror versions can throw on cleanup
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

async function loadTables(database: string) {
  try {
    const res = await queryApi.listTables(database);
    const tables = (res || []).map((t: any) => ({ name: typeof t === "string" ? t : t.name }));
    treeData.value = [{ name: database, children: tables }];
  } catch {
    treeData.value = [];
  }
}

function onDatabaseChange(db: string) {
  loadTables(db);
}

function handleNodeClick(data: TreeNode) {
  if (data.children) return;
  const sql = `SELECT * FROM ${currentDatabase.value}.${data.name} LIMIT 100;`;
  sqlText.value = sql;
  if (cmInstance) {
    cmInstance.setValue(sql);
  }
}

function filterNode(value: string, data: any) {
  if (!value) return true;
  return data.name.includes(value);
}

async function executeQuery() {
  const sql = cmInstance ? cmInstance.getValue() : sqlText.value;
  if (!sql.trim()) {
    ElMessage.warning("请输入SQL语句");
    return;
  }
  executing.value = true;
  try {
    const res = await queryApi.execute(sql, currentDatabase.value, limit.value);
    queryResult.value = res;
    ElMessage.success(`查询成功,返回 ${res.row_count} 行`);
  } catch {
    // handled
  } finally {
    executing.value = false;
  }
}

function openSaveDialog() {
  saveForm.query_name = "";
  saveForm.description = "";
  saveForm.tags = "";
  saveDialogVisible.value = true;
}

async function handleSaveQuery() {
  if (!saveForm.query_name) {
    ElMessage.warning("请输入查询名称");
    return;
  }
  const sql = cmInstance ? cmInstance.getValue() : sqlText.value;
  try {
    await queryApi.saveQuery({
      query_name: saveForm.query_name,
      sql_text: sql,
      database: currentDatabase.value,
      description: saveForm.description,
      tags: saveForm.tags,
    });
    ElMessage.success("保存成功");
    saveDialogVisible.value = false;
  } catch {
    // handled
  }
}

async function openHistoryDialog() {
  historyDialogVisible.value = true;
  await loadHistory();
}

async function loadHistory() {
  try {
    const res = await queryApi.history({ page: historyPagination.page, page_size: 20 });
    historyData.value = res.items || [];
    historyPagination.total = res.total || 0;
  } catch {
    // handled
  }
}
</script>

<style lang="scss" scoped>
.query-workbench {
  height: 100%;
}

.schema-browser {
  height: calc(100vh - 130px);
  overflow-y: auto;
}

.sql-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.sql-editor {
  :deep(.CodeMirror) {
    font-family: "Courier New", monospace;
    font-size: 14px;
    height: auto;
    min-height: 220px;
  }
}

.query-result {
  margin-top: 16px;

  .result-info {
    display: flex;
    gap: 16px;
    margin-bottom: 8px;
    font-size: 13px;
    color: #909399;

    .truncated-warning {
      color: #e6a23c;
    }
  }
}
</style>
