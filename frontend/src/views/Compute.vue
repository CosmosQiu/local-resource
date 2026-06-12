<template>
  <div class="compute-page">
    <div class="toolbar">
      <el-select v-model="filterType" placeholder="类型筛选" clearable @change="fetchResources" style="width:160px">
        <el-option label="裸金属" value="bare_metal" />
        <el-option label="K8s 集群" value="k8s_cluster" />
        <el-option label="Linux 主机" value="linux_host" />
        <el-option label="Windows 主机" value="windows_host" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchResources" style="width:140px;margin-left:10px">
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
        <el-option label="维护中" value="maintenance" />
      </el-select>
      <el-button v-if="auth.hasPermission('compute.manage')" type="primary" style="margin-left:auto" @click="openCreate">
        <el-icon><Plus /></el-icon> 添加资源
      </el-button>
    </div>

    <el-table :data="resources" v-loading="loading" stripe style="margin-top:16px">
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="resource_type" label="类型" width="100">
        <template #default="{ row }">{{ typeLabel(row.resource_type) }}</template>
      </el-table-column>
      <el-table-column prop="host_ip" label="IP" width="140" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status==='online'?'success':row.status==='maintenance'?'warning':'info'">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="GPU" width="200">
        <template #default="{ row }">
          <template v-if="row.gpus?.length">
            <el-tag v-for="g in row.gpus" :key="g.id" size="small" style="margin:2px">
              {{ g.gpu_name || `GPU#${g.gpu_index}` }} {{ g.utilization_pct }}%
            </el-tag>
          </template>
          <span v-else style="color:#909399">—</span>
        </template>
      </el-table-column>
      <el-table-column label="CPU" width="100">
        <template #default="{ row }">{{ row.available_cpu_cores }}/{{ row.total_cpu_cores }}</template>
      </el-table-column>
      <el-table-column label="内存(GB)" width="120">
        <template #default="{ row }">{{ row.available_memory_gb }}/{{ row.total_memory_gb }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="auth.hasPermission('compute.manage')" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="auth.hasPermission('compute.manage')" link type="danger" size="small" @click="deleteResource(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId?'编辑资源':'添加资源'" width="560px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" prop="resource_type">
          <el-select v-model="form.resource_type" style="width:100%">
            <el-option value="bare_metal" label="裸金属" />
            <el-option value="k8s_cluster" label="K8s 集群" />
            <el-option value="linux_host" label="Linux 主机" />
            <el-option value="windows_host" label="Windows 主机" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP"><el-input v-model="form.host_ip" /></el-form-item>
        <el-form-item label="CPU 核数"><el-input-number v-model="form.total_cpu_cores" :min="0" /></el-form-item>
        <el-form-item label="内存(GB)"><el-input-number v-model="form.total_memory_gb" :min="0" :step="0.5" /></el-form-item>
        <el-form-item label="磁盘(GB)"><el-input-number v-model="form.total_disk_gb" :min="0" /></el-form-item>
        <el-form-item label="GPUStack ID"><el-input v-model="form.gpustack_worker_id" placeholder="可选" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">{{ editingId?'保存':'创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { computeApi, type ComputeResource } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const auth = useAuthStore();
const resources = ref<ComputeResource[]>([]);
const loading = ref(false);
const filterType = ref("");
const filterStatus = ref("");

async function fetchResources() {
  loading.value = true;
  try {
    const { data } = await computeApi.list({ resource_type: filterType.value || undefined, status: filterStatus.value || undefined });
    resources.value = data.items;
  } finally { loading.value = false; }
}

const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({ name: "", resource_type: "", host_ip: "", total_cpu_cores: 0, total_memory_gb: 0, total_disk_gb: 0, gpustack_worker_id: "", notes: "" });
const rules: FormRules = { name: [{ required: true, message: "请输入名称" }], resource_type: [{ required: true, message: "请选择类型" }] };

function resetForm() { editingId.value = null; Object.assign(form, { name: "", resource_type: "", host_ip: "", total_cpu_cores: 0, total_memory_gb: 0, total_disk_gb: 0, gpustack_worker_id: "", notes: "" }); formRef.value?.resetFields(); }
function openCreate() { resetForm(); dialogVisible.value = true; }
function openEdit(row: ComputeResource) { resetForm(); editingId.value = row.id; form.name = row.name; form.resource_type = row.resource_type; form.host_ip = row.host_ip || ""; form.total_cpu_cores = row.total_cpu_cores; form.total_memory_gb = row.total_memory_gb; form.total_disk_gb = row.total_disk_gb; form.gpustack_worker_id = row.gpustack_worker_id || ""; form.notes = row.notes || ""; dialogVisible.value = true; }

async function submitForm() {
  if (!formRef.value) return;
  if (!(await formRef.value.validate().catch(() => false))) return;
  saving.value = true;
  try {
    if (editingId.value) { await computeApi.update(editingId.value, form); ElMessage.success("已更新"); }
    else { await computeApi.create(form); ElMessage.success("已创建"); }
    dialogVisible.value = false; fetchResources();
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || "操作失败"); }
  finally { saving.value = false; }
}

async function deleteResource(row: ComputeResource) {
  try { await ElMessageBox.confirm(`确定删除「${row.name}」？`, "确认", { type: "warning" }); await computeApi.delete(row.id); ElMessage.success("已删除"); fetchResources(); } catch { /* cancelled */ }
}

function typeLabel(t: string) { const m: Record<string,string> = { bare_metal: "裸金属", k8s_cluster: "K8s", linux_host: "Linux", windows_host: "Windows" }; return m[t] || t; }

onMounted(fetchResources);
</script>

<style scoped>
.compute-page { height:100%; }
.toolbar { display:flex; align-items:center; }
</style>
