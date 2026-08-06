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
            <el-select v-model="currentDatabase" placeholder="选择数据库" size="small" style="width: 150px;">
              <el-option v-for="db in databases" :key="db.name" :label="db.name" :value="db.name" />
            </el-select>
            <el-input-number v-model="limit" :min="1" :max="100000" :step="1000" size="small" style="width: 130px;" />
            <el-button type="primary" size="small" :icon="VideoPlay" @click="executeQuery" :loading="executing">
              执行
            </el-button>
            <el-button size="small" :icon="Document">保存查询</el-button>
            <el-button size="small" :icon="Clock">历史</el-button>
          </div>

          <!-- SQL Editor (placeholder: use textarea in MVP, upgrade to CodeMirror later) -->
          <el-input
            v-model="sqlText"
            type="textarea"
            :rows="10"
            placeholder="输入 SELECT 语句..."
            class="sql-editor"
          />

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
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { Search, VideoPlay, Document, Clock } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { queryApi } from "@/api";

const treeRef = ref();
const searchKeyword = ref("");
const databases = ref([]);
const currentDatabase = ref("");
const sqlText = ref("SELECT * FROM ods.ods_user LIMIT 100;");
const limit = ref(10000);
const executing = ref(false);
const queryResult = ref<any>(null);
const treeData = ref([]);

watch(searchKeyword, (val) => {
  treeRef.value?.filter(val);
});

onMounted(async () => {
  try {
    databases.value = await queryApi.listDatabases();
    if (databases.value.length > 0) {
      currentDatabase.value = databases.value[0].name;
      await loadTables(currentDatabase.value);
    }
  } catch {
    // API not ready
  }
});

async function loadTables(database: string) {
  const tables = await queryApi.listTables(database);
  treeData.value = [{ name: database, children: tables.map((t: any) => ({ name: t.name })) }];
}

function handleNodeClick(data: any) {
  if (data.children) return; // database node
  sqlText.value = `SELECT * FROM ${currentDatabase.value}.${data.name} LIMIT 100;`;
}

function filterNode(value: string, data: any) {
  if (!value) return true;
  return data.name.includes(value);
}

async function executeQuery() {
  if (!sqlText.value.trim()) {
    ElMessage.warning("请输入SQL语句");
    return;
  }
  executing.value = true;
  try {
    queryResult.value = await queryApi.execute(sqlText.value, currentDatabase.value, limit.value);
    ElMessage.success(`查询成功,返回 ${queryResult.value.row_count} 行`);
  } catch {
    // handled
  } finally {
    executing.value = false;
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
  :deep(.el-textarea__inner) {
    font-family: "Courier New", monospace;
    font-size: 14px;
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
