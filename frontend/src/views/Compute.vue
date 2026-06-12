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
      <el-table-column prop="ssh_username" label="SSH 用户" width="110" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status==='online'?'success':row.status==='maintenance'?'warning':'info'">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="监控初始化" width="110">
        <template #default="{ row }">
          <el-tag :type="row.init_status==='done'?'success':row.init_status==='pending'?'warning':'info'" size="small">
            {{ row.init_status === 'done' ? '已完成' : row.init_status === 'pending' ? '待初始化' : row.init_status || '—' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="CPU" width="100">
        <template #default="{ row }">{{ row.available_cpu_cores }}/{{ row.total_cpu_cores }}</template>
      </el-table-column>
      <el-table-column label="内存(GB)" width="120">
        <template #default="{ row }">{{ row.available_memory_gb }}/{{ row.total_memory_gb }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" size="small" @click="showInitCommand(row)">
            <el-icon><Monitor /></el-icon> 初始化指令
          </el-button>
          <el-button v-if="auth.hasPermission('compute.manage')" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="auth.hasPermission('compute.manage')" link type="danger" size="small" @click="deleteResource(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create / Edit Dialog -->
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
        <el-form-item label="IP 地址"><el-input v-model="form.host_ip" placeholder="例如 192.168.1.100" /></el-form-item>
        <el-form-item label="SSH 用户名"><el-input v-model="form.ssh_username" placeholder="root" /></el-form-item>
        <el-form-item label="SSH 密码"><el-input v-model="form.ssh_password" type="password" placeholder="目标主机 SSH 密码" show-password /></el-form-item>
        <el-form-item label="CPU 核数"><el-input-number v-model="form.total_cpu_cores" :min="0" /></el-form-item>
        <el-form-item label="内存(GB)"><el-input-number v-model="form.total_memory_gb" :min="0" :step="0.5" /></el-form-item>
        <el-form-item label="磁盘(GB)"><el-input-number v-model="form.total_disk_gb" :min="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">{{ editingId?'保存':'创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Init Command Dialog -->
    <el-dialog v-model="initDialogVisible" title="初始化指令 — Node Exporter 安装" width="700px">
      <div v-if="initLoading" style="text-align:center;padding:20px"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>
      <template v-else-if="initData">
        <el-alert v-if="initData.init_status === 'done'" title="该主机已完成初始化" type="success" :closable="false" style="margin-bottom:12px" />
        <el-alert v-else title="请在目标主机上执行以下命令以安装 node_exporter" type="warning" :closable="false" style="margin-bottom:12px" />
        <div style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
          <span><strong>目标主机：</strong>{{ initData.host_ip }}</span>
          <el-button size="small" @click="copyCommand">复制命令</el-button>
        </div>
        <el-input
          :model-value="initData.init_command || '暂无初始化指令'"
          type="textarea"
          :rows="14"
          readonly
          style="font-family:monospace;font-size:13px"
        />
        <div v-if="initData.grafana_url" style="margin-top:8px">
          <strong>Grafana 面板：</strong>
          <el-link type="primary" :href="initData.grafana_url" target="_blank">{{ initData.grafana_url }}</el-link>
        </div>
      </template>
      <template #footer><el-button @click="initDialogVisible=false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { computeApi, type ComputeResource, type InitCommandResponse } from "@/api/client";
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

// ---------- Create / Edit ----------
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({
  name: "", resource_type: "", host_ip: "",
  ssh_username: "", ssh_password: "",
  total_cpu_cores: 0, total_memory_gb: 0, total_disk_gb: 0,
  notes: "",
});
const rules: FormRules = {
  name: [{ required: true, message: "请输入名称" }],
  resource_type: [{ required: true, message: "请选择类型" }],
};

function resetForm() {
  editingId.value = null;
  Object.assign(form, { name: "", resource_type: "", host_ip: "", ssh_username: "", ssh_password: "", total_cpu_cores: 0, total_memory_gb: 0, total_disk_gb: 0, notes: "" });
  formRef.value?.resetFields();
}
function openCreate() { resetForm(); dialogVisible.value = true; }
function openEdit(row: ComputeResource) {
  resetForm();
  editingId.value = row.id;
  form.name = row.name;
  form.resource_type = row.resource_type;
  form.host_ip = row.host_ip || "";
  form.ssh_username = row.ssh_username || "";
  form.total_cpu_cores = row.total_cpu_cores;
  form.total_memory_gb = row.total_memory_gb;
  form.total_disk_gb = row.total_disk_gb;
  form.notes = row.notes || "";
  dialogVisible.value = true;
}

async function submitForm() {
  if (!formRef.value) return;
  if (!(await formRef.value.validate().catch(() => false))) return;
  saving.value = true;
  try {
    if (editingId.value) { await computeApi.update(editingId.value, form); ElMessage.success("已更新"); }
    else { await computeApi.create(form); ElMessage.success("已创建，请在主机上执行初始化指令"); }
    dialogVisible.value = false; fetchResources();
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || "操作失败"); }
  finally { saving.value = false; }
}

async function deleteResource(row: ComputeResource) {
  try { await ElMessageBox.confirm(`确定删除「${row.name}」？`, "确认", { type: "warning" }); await computeApi.delete(row.id); ElMessage.success("已删除"); fetchResources(); } catch { /* cancelled */ }
}

// ---------- Init Command ----------
const initDialogVisible = ref(false);
const initLoading = ref(false);
const initData = ref<InitCommandResponse | null>(null);

async function showInitCommand(row: ComputeResource) {
  initDialogVisible.value = true;
  initLoading.value = true;
  initData.value = null;
  try {
    const { data } = await computeApi.getInitCommand(row.id);
    initData.value = data;
  } catch { initData.value = { resource_id: row.id, resource_name: row.name, host_ip: row.host_ip || "", init_command: null, init_status: "pending", grafana_url: null }; }
  finally { initLoading.value = false; }
}

async function copyCommand() {
  if (!initData.value?.init_command) return;
  try {
    await navigator.clipboard.writeText(initData.value.init_command);
    ElMessage.success("已复制到剪贴板");
  } catch { ElMessage.warning("复制失败，请手动选择复制"); }
}

function typeLabel(t: string) { const m: Record<string,string> = { bare_metal: "裸金属", k8s_cluster: "K8s", linux_host: "Linux", windows_host: "Windows" }; return m[t] || t; }

onMounted(fetchResources);
</script>

<style scoped>
.compute-page { height:100%; }
.toolbar { display:flex; align-items:center; }
</style>
