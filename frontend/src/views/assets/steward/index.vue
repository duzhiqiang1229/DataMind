<template>
  <div class="table-steward">
    <el-alert v-if="omHealthy" type="info" :closable="false" show-icon class="om-tip">
      OpenMetadata 已接管统一责任人和业务域治理；本页保留 DataMind 本地责任人作为补充映射。
    </el-alert>
    <el-row v-if="omHealthy" :gutter="12" class="governance-overview">
      <el-col :span="8"><el-card shadow="never"><b>{{ omSummary.coverage?.owners || 0 }}%</b><span>资产责任人覆盖率</span></el-card></el-col>
      <el-col :span="8"><el-card shadow="never"><b>{{ omGovernance.domains?.length || 0 }}</b><span>OpenMetadata 业务域</span></el-card></el-col>
      <el-col :span="8"><el-card shadow="never"><b>{{ omGovernance.dataProducts?.length || 0 }}</b><span>已登记数据产品</span></el-card></el-col>
    </el-row>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据责任人</span>
          <div class="header-actions">
            <el-select
              v-model="filterDatabase"
              placeholder="按数据库筛选"
              clearable
              filterable
              size="small"
              style="width: 200px"
              @change="loadOwners"
            >
              <el-option v-for="db in databaseOptions" :key="db" :label="db" :value="db" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="openDialog(null)">新增责任人</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="ownerList" border stripe>
        <el-table-column prop="database_name" label="数据库" min-width="160" show-overflow-tooltip />
        <el-table-column prop="table_name" label="表名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="owner_name" label="责任人" min-width="140" show-overflow-tooltip />
        <el-table-column label="类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getOwnerTagType(row.owner_type)" size="small" effect="plain">
              {{ formatOwnerType(row.owner_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contact" label="联系方式" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="deleteOwner(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadOwners"
          @current-change="loadOwners"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑责任人' : '新增责任人'" width="760px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-width="70px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="数据库" required>
              <el-select
                v-if="databaseOptions.length"
                v-model="form.database_name"
                placeholder="选择数据库"
                filterable
                allow-create
                style="width: 100%"
              >
                <el-option v-for="db in databaseOptions" :key="db" :label="db" :value="db" />
              </el-select>
              <el-input v-else v-model="form.database_name" placeholder="请输入数据库名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="表名" required>
              <el-input v-model="form.table_name" placeholder="请输入表名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="责任人" required>
              <el-input v-model="form.owner_name" placeholder="请输入责任人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" required>
              <el-select v-model="form.owner_type" placeholder="请选择类型" style="width: 100%">
                <el-option label="个人" value="person" />
                <el-option label="团队" value="team" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="联系方式">
              <el-input v-model="form.contact" placeholder="邮箱/电话/钉钉等" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveOwner">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import { tableOwnerApi, queryApi, openmetadataApi } from "@/api";

type TagType = "primary" | "success" | "info" | "warning" | "danger";

interface OwnerRow {
  id?: string;
  database_name: string;
  table_name: string;
  owner_name: string;
  owner_type: string;
  contact?: string;
}

const loading = ref(false);
const saving = ref(false);
const ownerList = ref<OwnerRow[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const filterDatabase = ref("");
const databaseOptions = ref<string[]>([]);
const omHealthy = ref(false);
const omSummary = ref<any>({ coverage: {} });
const omGovernance = ref<any>({ domains: [], dataProducts: [] });

const dialogVisible = ref(false);
const form = ref<OwnerRow>({ database_name: "", table_name: "", owner_name: "", owner_type: "person", contact: "" });

const getOwnerTagType = (type: string): TagType => {
  return type === "team" ? "warning" : "success";
};

const formatOwnerType = (type: string): string => {
  if (type === "team") return "团队";
  if (type === "person") return "个人";
  return type || "—";
};

const loadDatabases = async () => {
  try {
    const res = await queryApi.listDatabases();
    const data = (res as any)?.data ?? res;
    databaseOptions.value = Array.isArray(data) ? data : (data?.items ?? []);
  } catch {
    databaseOptions.value = [];
  }
};

const loadOwners = async () => {
  loading.value = true;
  try {
    const params: any = { page: page.value, page_size: pageSize.value };
    if (filterDatabase.value) params.database_name = filterDatabase.value;
    const res = await tableOwnerApi.list(params);
    const data = (res as any)?.data ?? res;
    ownerList.value = data?.items ?? (Array.isArray(data) ? data : []);
    total.value = data?.total ?? ownerList.value.length;
  } catch {
    ElMessage.error("加载责任人列表失败");
    ownerList.value = [];
  } finally {
    loading.value = false;
  }
};

const openDialog = (row: OwnerRow | null | any) => {
  if (row) {
    form.value = { ...row };
  } else {
    form.value = {
      database_name: filterDatabase.value || "",
      table_name: "",
      owner_name: "",
      owner_type: "person",
      contact: "",
    };
  }
  dialogVisible.value = true;
};

const saveOwner = async () => {
  if (!form.value.database_name || !form.value.table_name || !form.value.owner_name) {
    ElMessage.warning("请填写完整信息");
    return;
  }
  saving.value = true;
  try {
    await tableOwnerApi.setOwner({ ...form.value });
    ElMessage.success("保存成功");
    dialogVisible.value = false;
    await loadOwners();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
};

const deleteOwner = async (row: OwnerRow | any) => {
  try {
    await ElMessageBox.confirm(`确认删除「${row.database_name}.${row.table_name}」的责任人设置？`, "提示", { type: "warning" });
    await tableOwnerApi.removeOwner(row.database_name, row.table_name);
    ElMessage.success("删除成功");
    await loadOwners();
  } catch (e) {
    if (e !== "cancel") ElMessage.error("删除失败");
  }
};

onMounted(() => {
  loadDatabases();
  loadOwners();
  Promise.all([openmetadataApi.health(), openmetadataApi.summary(), openmetadataApi.governance()])
    .then(([health, summary, governance]: any[]) => {
      omHealthy.value = !!health?.healthy;
      omSummary.value = summary || omSummary.value;
      omGovernance.value = governance || omGovernance.value;
    })
    .catch(() => { omHealthy.value = false; });
});
</script>

<style lang="scss" scoped>
.table-steward {
  padding: 16px;

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .pagination {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .om-tip { margin-bottom: 12px; }

  .governance-overview {
    margin-bottom: 12px;

    :deep(.el-card__body) { display: flex; align-items: baseline; gap: 10px; }
    b { font-size: 24px; color: #409eff; }
    span { color: #606266; }
  }
}
</style>
