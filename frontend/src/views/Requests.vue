<template>
  <div class="requests-page">
    <div class="toolbar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="fetchRequests" style="width:140px">
        <el-option label="待审批" value="pending" /><el-option label="已通过" value="approved" />
        <el-option label="运行中" value="running" /><el-option label="已拒绝" value="rejected" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-button v-if="auth.hasPermission('compute.request')" type="primary" style="margin-left:auto" @click="openCreate">
        <el-icon><Plus /></el-icon> 申请资源
      </el-button>
    </div>

    <el-table :data="requests" v-loading="loading" stripe style="margin-top:16px">
      <el-table-column prop="username" label="申请人" width="100" />
      <el-table-column label="类型" width="100"><template #default="{row}">{{ row.request_type==='container'?'容器':'裸金属' }}</template></el-table-column>
      <el-table-column label="规格" min-width="200">
        <template #default="{row}">{{ row.cpu_cores }}C / {{ row.memory_gb }}G / {{ row.disk_gb }}G{{ row.gpu_count>0 ? ` / ${row.gpu_count}×GPU` : '' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{row}"><el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="申请时间" width="160"><template #default="{row}">{{ fmt(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{row}">
          <el-button v-if="row.status==='pending' && auth.hasPermission('compute.approve')" link type="success" size="small" @click="approve(row,true)">通过</el-button>
          <el-button v-if="row.status==='pending' && auth.hasPermission('compute.approve')" link type="danger" size="small" @click="approve(row,false)">拒绝</el-button>
          <el-button v-if="row.status==='running' && row.user_id===auth.user?.id" link type="danger" size="small" @click="stopRequest(row)">停止</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="申请资源" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="类型" prop="request_type"><el-radio-group v-model="form.request_type"><el-radio value="container">容器</el-radio><el-radio value="bare_metal">裸金属</el-radio></el-radio-group></el-form-item>
        <el-form-item label="CPU 核数"><el-input-number v-model="form.cpu_cores" :min="1" /></el-form-item>
        <el-form-item label="内存(GB)"><el-input-number v-model="form.memory_gb" :min="0.5" :step="0.5" /></el-form-item>
        <el-form-item label="磁盘(GB)"><el-input-number v-model="form.disk_gb" :min="1" /></el-form-item>
        <el-form-item label="GPU 数量"><el-input-number v-model="form.gpu_count" :min="0" /></el-form-item>
        <el-form-item label="镜像" v-if="form.request_type==='container'"><el-input v-model="form.image_name" placeholder="如 nvidia/cuda:12.4-devel" /></el-form-item>
        <el-form-item label="端口映射" v-if="form.request_type==='container'"><el-input v-model="form.exposed_ports_text" placeholder='如 {"8888/tcp":30080}' /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="submitForm">提交申请</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { requestsApi, type ContainerRequest } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const auth = useAuthStore();
const requests = ref<ContainerRequest[]>([]);
const loading = ref(false);
const filterStatus = ref("");

async function fetchRequests() {
  loading.value = true;
  try { const { data } = await requestsApi.list({ status: filterStatus.value || undefined }); requests.value = data.items; }
  finally { loading.value = false; }
}

const dialogVisible = ref(false);
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({ request_type: "container", cpu_cores: 2, memory_gb: 4, disk_gb: 20, gpu_count: 0, image_name: "", exposed_ports_text: "" });
const rules: FormRules = { request_type: [{ required: true }] };

function openCreate() { Object.assign(form, { request_type: "container", cpu_cores: 2, memory_gb: 4, disk_gb: 20, gpu_count: 0, image_name: "", exposed_ports_text: "" }); dialogVisible.value = true; }

async function submitForm() {
  if (!formRef.value) return;
  if (!(await formRef.value.validate().catch(() => false))) return;
  saving.value = true;
  try {
    let exposed_ports = null;
    if (form.exposed_ports_text) { try { exposed_ports = JSON.parse(form.exposed_ports_text); } catch { ElMessage.error("端口映射格式错误"); saving.value = false; return; } }
    await requestsApi.create({ ...form, exposed_ports, exposed_ports_text: undefined });
    ElMessage.success("申请已提交"); dialogVisible.value = false; fetchRequests();
  } catch (e: any) { ElMessage.error(e.response?.data?.detail || "提交失败"); }
  finally { saving.value = false; }
}

async function approve(row: ContainerRequest, approved: boolean) {
  try { await requestsApi.approve(row.id, approved); ElMessage.success(approved ? "已通过" : "已拒绝"); fetchRequests(); }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || "操作失败"); }
}

async function stopRequest(row: ContainerRequest) {
  try { await requestsApi.stop(row.id); ElMessage.success("已停止"); fetchRequests(); }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || "操作失败"); }
}

function statusTag(s: string) { const m: Record<string,string> = { pending:"warning", approved:"success", running:"", rejected:"danger", completed:"info" }; return m[s]||"info"; }
function statusLabel(s: string) { const m: Record<string,string> = { pending:"待审批", approved:"已通过", running:"运行中", rejected:"已拒绝", completed:"已完成" }; return m[s]||s; }
function fmt(iso: string) { return iso ? new Date(iso).toLocaleString("zh-CN") : ""; }

onMounted(fetchRequests);
</script>

<style scoped>
.requests-page { height:100%; }
.toolbar { display:flex; align-items:center; }
</style>
