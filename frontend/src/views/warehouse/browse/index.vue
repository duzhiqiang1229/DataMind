<template>
  <div class="warehouse-browse">
    <el-row :gutter="16">
      <!-- 左侧: 库表树 -->
      <el-col :span="8">
        <el-card class="tree-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>库表浏览</span>
              <el-button :icon="Refresh" size="small" circle @click="loadDatabases" />
            </div>
          </template>
          <el-input v-model="searchKeyword" placeholder="搜索表名" :prefix-icon="Search" clearable size="small" style="margin-bottom: 8px;" />
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ label: 'name', children: 'children' }"
            node-key="key"
            @node-click="handleNodeClick"
            :filter-node-method="filterNode"
            :expand-on-click-node="false"
            v-loading="treeLoading"
          />
        </el-card>
      </el-col>

      <!-- 右侧: 表结构 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span v-if="currentTable">{{ currentDatabase }}.{{ currentTable }}</span>
              <span v-else>请选择一个表</span>
            </div>
          </template>

          <div v-if="currentTable" v-loading="columnsLoading">
            <el-table :data="columns" border size="small">
              <el-table-column prop="name" label="列名" width="180" />
              <el-table-column prop="type" label="类型" width="150" />
              <el-table-column prop="comment" label="注释" min-width="200" show-overflow-tooltip />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="previewData(row)">预览</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div style="margin-top: 16px;">
              <el-button type="primary" size="small" @click="openQueryWorkbench">
                在 SQL 工作台查询
              </el-button>
            </div>
          </div>
          <el-empty v-else description="选择左侧的表查看结构" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { Search, Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { queryApi } from "@/api";

interface TreeNode {
  name: string;
  key: string;
  children?: TreeNode[];
  isDatabase?: boolean;
}

const router = useRouter();
const treeRef = ref();
const searchKeyword = ref("");
const treeData = ref<TreeNode[]>([]);
const treeLoading = ref(false);
const currentDatabase = ref("");
const currentTable = ref("");
const columns = ref<any[]>([]);
const columnsLoading = ref(false);

watch(searchKeyword, (val) => {
  treeRef.value?.filter(val);
});

onMounted(loadDatabases);

async function loadDatabases() {
  treeLoading.value = true;
  try {
    const dbs = await queryApi.listDatabases();
    treeData.value = (dbs || []).map((db: any) => {
      const name = typeof db === "string" ? db : db.name;
      return {
        name,
        key: `db_${name}`,
        isDatabase: true,
        children: [],
      };
    });
  } catch { /* handled */ } finally {
    treeLoading.value = false;
  }
}

async function handleNodeClick(data: TreeNode) {
  if (data.isDatabase) {
    // load tables for this database
    currentDatabase.value = data.name;
    if (!data.children || data.children.length === 0) {
      try {
        const tables = await queryApi.listTables(data.name);
        data.children = (tables || []).map((t: any) => {
          const name = typeof t === "string" ? t : t.name;
          return { name, key: `tbl_${data.name}_${name}` };
        });
      } catch { /* handled */ }
    }
    currentTable.value = "";
    columns.value = [];
  } else {
    // table node clicked — load columns
    const parentDb = treeData.value.find((db) =>
      db.children?.some((c) => c.key === data.key)
    );
    if (parentDb) {
      currentDatabase.value = parentDb.name;
    }
    currentTable.value = data.name;
    await loadColumns();
  }
}

async function loadColumns() {
  if (!currentDatabase.value || !currentTable.value) return;
  columnsLoading.value = true;
  try {
    const res = await queryApi.getTableSchema(currentDatabase.value, currentTable.value);
    columns.value = (res || []).map((col: any) => {
      if (typeof col === "string") return { name: col, type: "", comment: "" };
      return { name: col.name || col.column_name, type: col.type || col.column_type || "", comment: col.comment || col.column_comment || "" };
    });
  } catch { /* handled */ } finally {
    columnsLoading.value = false;
  }
}

function previewData(row: any) {
  // Navigate to query workbench with a pre-filled query
  router.push({
    path: "/query",
    query: { db: currentDatabase.value, table: currentTable.value },
  });
}

function openQueryWorkbench() {
  router.push({
    path: "/query",
    query: { db: currentDatabase.value, table: currentTable.value },
  });
}

function filterNode(value: string, data: any) {
  if (!value) return true;
  return data.name.includes(value);
}
</script>

<style lang="scss" scoped>
.warehouse-browse { height: 100%; }
.tree-card { height: calc(100vh - 130px); overflow-y: auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
