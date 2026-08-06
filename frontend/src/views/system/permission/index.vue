<template>
  <div class="permission-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>权限管理</span>
          <div class="filter-bar">
            <el-select
              v-model="resourceFilter"
              placeholder="筛选资源类型"
              clearable
              style="width: 200px;"
              @change="applyFilter"
            >
              <el-option
                v-for="res in resourceTypes"
                :key="res"
                :label="res"
                :value="res"
              />
            </el-select>
            <el-input
              v-model="keyword"
              placeholder="搜索权限名称/编码"
              clearable
              style="width: 220px;"
              @input="applyFilter"
            />
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 16px;"
      >
        权限由系统种子数据预定义，不可新增或删除。如需调整请联系管理员修改种子配置。
      </el-alert>

      <el-table
        :data="filteredData"
        v-loading="loading"
        border
        :span-method="spanMethod"
        :row-class-name="rowClassName"
      >
        <el-table-column prop="resource" label="资源" width="140" />
        <el-table-column prop="permission_code" label="权限编码" min-width="180" />
        <el-table-column prop="permission_name" label="权限名称" min-width="160" />
        <el-table-column prop="action" label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small">
              {{ row.action }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column label="关联角色" width="120" align="center">
          <template #default="{ row }">
            <el-tooltip
              v-if="getRolesForPermission(row.id).length > 0"
              :content="getRolesForPermission(row.id).join(', ')"
              placement="top"
            >
              <el-tag :type="getRoleCountTagType(getRolesForPermission(row.id).length)" size="small">
                {{ getRolesForPermission(row.id).length }} 个角色
              </el-tag>
            </el-tooltip>
            <el-tag v-else type="info" size="small">无</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="summary">
        <span>共 {{ permissions.length }} 项权限</span>
        <span>资源类型 {{ resourceTypes.length }} 种</span>
        <span>已分配角色 {{ assignedPermissionCount }} 项</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { roleApi } from "@/api";

type TagType = "primary" | "success" | "warning" | "info" | "danger";

interface Permission {
  id: string;
  permission_code: string;
  permission_name: string;
  resource: string;
  action: string;
  description: string;
}

interface Role {
  id: string;
  role_name: string;
  role_code: string;
  permissions?: Permission[];
}

const loading = ref(false);
const permissions = ref<Permission[]>([]);
const roles = ref<Role[]>([]);
const resourceFilter = ref("");
const keyword = ref("");

// Group-sorted data for display with span merging
const displayData = ref<Permission[]>([]);
// Track span info: index → rowspan for the resource column
const spanMap = ref<Map<number, number>>(new Map());
const groupStartIndices = ref<number[]>([]);

const resourceTypes = computed(() => {
  const set = new Set(permissions.value.map((p) => p.resource));
  return Array.from(set).sort();
});

const filteredData = computed(() => {
  let data = permissions.value;

  if (resourceFilter.value) {
    data = data.filter((p) => p.resource === resourceFilter.value);
  }

  if (keyword.value.trim()) {
    const kw = keyword.value.toLowerCase();
    data = data.filter(
      (p) =>
        p.permission_name.toLowerCase().includes(kw) ||
        p.permission_code.toLowerCase().includes(kw),
    );
  }

  // Sort by resource, then by action, then by permission_code for stable grouping
  data = [...data].sort((a, b) => {
    if (a.resource !== b.resource) return a.resource.localeCompare(b.resource);
    if (a.action !== b.action) return a.action.localeCompare(b.action);
    return a.permission_code.localeCompare(b.permission_code);
  });

  return data;
});

const assignedPermissionCount = computed(() => {
  const assignedIds = new Set<string>();
  roles.value.forEach((r) => {
    (r.permissions || []).forEach((p) => {
      if (typeof p === "object" && p.id) {
        assignedIds.add(p.id);
      } else if (typeof p === "string") {
        assignedIds.add(p);
      }
    });
  });
  return permissions.value.filter((p) => assignedIds.has(p.id)).length;
});

function actionTagType(action: string): TagType {
  const map: Record<string, TagType> = {
    create: "success",
    read: "info",
    update: "warning",
    delete: "danger",
    manage: "primary",
    execute: "primary",
    view: "info",
    edit: "warning",
  };
  return map[action.toLowerCase()] || "info";
}

function getRoleCountTagType(count: number): TagType {
  if (count >= 5) return "danger";
  if (count >= 3) return "warning";
  if (count >= 1) return "success";
  return "info";
}

function getRolesForPermission(permissionId: string): string[] {
  const result: string[] = [];
  roles.value.forEach((r) => {
    const has = (r.permissions || []).some((p: any) => p?.id === permissionId);
    if (has) result.push(r.role_name);
  });
  return result;
}

function rebuildSpanMap() {
  const data = filteredData.value;
  const map = new Map<number, number>();
  const starts: number[] = [];

  let i = 0;
  while (i < data.length) {
    const resource = data[i].resource;
    let count = 0;
    while (i + count < data.length && data[i + count].resource === resource) {
      count++;
    }
    map.set(i, count);
    starts.push(i);
    if (count > 1) {
      for (let j = 1; j < count; j++) {
        map.set(i + j, 0);
      }
    }
    i += count;
  }

  spanMap.value = map;
  groupStartIndices.value = starts;
  displayData.value = data;
}

function spanMethod({ row, rowIndex, columnIndex }: { row: Permission; rowIndex: number; columnIndex: number }) {
  if (columnIndex === 0) {
    const span = spanMap.value.get(rowIndex);
    if (span === 0) {
      return { rowspan: 0, colspan: 0 };
    }
    return { rowspan: span || 1, colspan: 1 };
  }
  return { rowspan: 1, colspan: 1 };
}

function rowClassName({ rowIndex }: { rowIndex: number }) {
  const groupIdx = groupStartIndices.value.indexOf(rowIndex);
  if (groupIdx === -1) return "";
  return groupIdx % 2 === 0 ? "group-even" : "group-odd";
}

function applyFilter() {
  rebuildSpanMap();
}

async function loadData() {
  loading.value = true;
  try {
    const [perms, roleList] = await Promise.all([
      roleApi.listPermissions(),
      roleApi.list(),
    ]);
    permissions.value = (perms || []) as Permission[];
    roles.value = (roleList || []) as Role[];
    rebuildSpanMap();
  } catch {
    /* handled by interceptor */
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style lang="scss" scoped>
.permission-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .filter-bar {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  }

  .summary {
    margin-top: 16px;
    display: flex;
    gap: 24px;
    font-size: 13px;
    color: #909399;
  }
}

:deep(.group-even) {
  background-color: #fafafa;
}

:deep(.group-odd) {
  background-color: #f5f7fa;
}
</style>
