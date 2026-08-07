<template>
  <el-card>
    <template #header>系统配置</template>
    <el-table :data="configData" v-loading="loading" border>
      <el-table-column prop="config_key" label="配置项" width="200" />
      <el-table-column label="值" min-width="200">
        <template #default="{ row }">
          <el-input v-if="row.editing" v-model="row.config_value" size="small" />
          <span v-else>{{ row.config_value }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="config_type" label="类型" width="80" />
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button v-if="!row.editing" text type="primary" size="small" @click="row.editing = true">编辑</el-button>
          <el-button v-else text type="success" size="small" @click="handleSave(row)">保存</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { systemApi } from "@/api";

const loading = ref(false);
const configData = ref<any[]>([]);

async function loadData() {
  loading.value = true;
  try {
    const res = await systemApi.listConfigs();
    configData.value = (res || []).map((c: any) => ({ ...c, editing: false }));
  } catch { /* handled */ } finally {
    loading.value = false;
  }
}

async function handleSave(row: any) {
  try {
    await systemApi.updateConfig(row.config_key, row.config_value);
    row.editing = false;
    ElMessage.success("保存成功");
  } catch { /* handled */ }
}

onMounted(loadData);
</script>
