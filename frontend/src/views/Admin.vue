<template>
  <div class="admin-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="用户管理" name="users">
        <el-table :data="users" v-loading="loadingU" stripe>
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="email" label="邮箱" width="200" />
          <el-table-column prop="display_name" label="显示名" width="120" />
          <el-table-column label="角色" min-width="200">
            <template #default="{row}"><el-tag v-for="r in row.roles" :key="r" size="small" style="margin:2px">{{ r }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{row}">
              <el-button link type="primary" size="small" @click="openRoleDialog(row)">分配角色</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="角色权限" name="roles">
        <el-table :data="roles" stripe>
          <el-table-column prop="name" label="角色" width="120" />
          <el-table-column prop="description" label="描述" width="200" />
          <el-table-column label="权限" min-width="300">
            <template #default="{row}"><el-tag v-for="p in row.permissions" :key="p" size="small" style="margin:2px">{{ p }}</el-tag></template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="roleDialogVisible" title="分配角色" width="400px">
      <el-checkbox-group v-model="selectedRoles">
        <el-checkbox v-for="r in allRoles" :key="r.id" :label="r.id" :value="r.id">{{ r.name }}</el-checkbox>
      </el-checkbox-group>
      <template #footer><el-button @click="roleDialogVisible=false">取消</el-button><el-button type="primary" @click="saveRoles">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { adminApi } from "@/api/client";
import { ElMessage } from "element-plus";

const activeTab = ref("users");
const users = ref<any[]>([]);
const roles = ref<any[]>([]);
const allRoles = ref<any[]>([]);
const loadingU = ref(false);
const roleDialogVisible = ref(false);
const selectedRoles = ref<number[]>([]);
const editingUserId = ref<number | null>(null);

async function fetchUsers() {
  loadingU.value = true;
  try { const { data } = await adminApi.listUsers(); users.value = data; }
  finally { loadingU.value = false; }
}

async function fetchRoles() {
  try { const { data } = await adminApi.listRoles(); roles.value = data; allRoles.value = data; }
  catch { /* 403 if no permission */ }
}

function openRoleDialog(user: any) {
  editingUserId.value = user.id;
  selectedRoles.value = (user.roles || []).map((r: string) => allRoles.value.find((a: any) => a.name === r)?.id).filter(Boolean);
  roleDialogVisible.value = true;
}

async function saveRoles() {
  if (!editingUserId.value) return;
  try {
    await adminApi.assignRoles(editingUserId.value, selectedRoles.value);
    ElMessage.success("角色已更新");
    roleDialogVisible.value = false;
    fetchUsers();
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || "操作失败"); }
}

onMounted(() => { fetchUsers(); fetchRoles(); });
</script>

<style scoped>
.admin-page { height:100%; }
</style>
