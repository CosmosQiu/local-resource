<template>
  <div class="accounts-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <el-select v-model="filterPlatform" placeholder="平台筛选" clearable style="width: 160px" @change="fetchAccounts">
        <el-option label="OpenAI" value="openai" />
        <el-option label="Claude" value="claude" />
        <el-option label="DeepSeek" value="deepseek" />
        <el-option label="Gemini" value="gemini" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px; margin-left: 10px" @change="fetchAccounts">
        <el-option label="正常" value="active" />
        <el-option label="已过期" value="expired" />
        <el-option label="异常" value="error" />
        <el-option label="已停用" value="suspended" />
      </el-select>
      <el-button
        v-if="auth.hasPermission('accounts.create')"
        type="primary"
        style="margin-left: auto"
        @click="openCreateDialog"
      >
        <el-icon><Plus /></el-icon>
        新增账号
      </el-button>
    </div>

    <!-- Table -->
    <el-table
      :data="accounts"
      v-loading="loading"
      stripe
      style="margin-top: 16px"
    >
      <el-table-column prop="platform" label="平台" width="100" />
      <el-table-column prop="account_name" label="账号名称" min-width="160" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="expiration_date" label="到期时间" width="160">
        <template #default="{ row }">
          <span v-if="row.expiration_date">
            {{ formatDate(row.expiration_date) }}
          </span>
          <span v-else style="color: #909399">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="last_verified_at" label="最后验证" width="160">
        <template #default="{ row }">
          <span v-if="row.last_verified_at">
            {{ formatDate(row.last_verified_at) }}
          </span>
          <span v-else style="color: #909399">未验证</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="auth.hasPermission('accounts.read_secret')"
            link
            type="primary"
            size="small"
            @click="viewSecret(row.id)"
          >
            查看凭证
          </el-button>
          <el-button
            v-if="auth.hasPermission('accounts.update')"
            link
            type="primary"
            size="small"
            @click="openEditDialog(row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="auth.hasPermission('accounts.delete')"
            link
            type="danger"
            size="small"
            @click="deleteAccount(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <el-pagination
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @current-change="fetchAccounts"
    />

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑账号' : '新增账号'"
      width="560px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="平台" prop="platform">
          <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Claude" value="claude" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="Gemini" value="gemini" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号名称" prop="account_name">
          <el-input v-model="form.account_name" placeholder="例如：公司 OpenAI 主账号" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="登录用户名（可选）" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="登录密码（可选）" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-...（可选）" />
        </el-form-item>
        <el-form-item label="Cookie">
          <el-input v-model="form.cookie_data" type="textarea" :rows="2" placeholder='JSON 格式 Cookie，用于到期检测（可选）' />
        </el-form-item>
        <el-form-item label="到期时间">
          <el-date-picker
            v-model="form.expiration_date"
            type="datetime"
            placeholder="选择到期时间（可选）"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Secret View Dialog -->
    <el-dialog
      v-model="secretVisible"
      title="查看凭证"
      width="500px"
    >
      <el-descriptions :column="1" border v-if="secretData">
        <el-descriptions-item label="用户名">
          <el-input :model-value="secretData.username || '—'" readonly />
        </el-descriptions-item>
        <el-descriptions-item label="密码">
          <el-input :model-value="secretData.password || '—'" readonly show-password />
        </el-descriptions-item>
        <el-descriptions-item label="API Key">
          <el-input :model-value="secretData.api_key || '—'" readonly show-password />
        </el-descriptions-item>
        <el-descriptions-item label="Cookie">
          <el-input :model-value="secretData.cookie_data || '—'" readonly type="textarea" :rows="3" />
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { accountsApi, type AIAccount, type AIAccountSecret } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const auth = useAuthStore();

// ---------- List ----------
const accounts = ref<AIAccount[]>([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const filterPlatform = ref("");
const filterStatus = ref("");

async function fetchAccounts() {
  loading.value = true;
  try {
    const { data } = await accountsApi.list({
      platform: filterPlatform.value || undefined,
      status: filterStatus.value || undefined,
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value,
    });
    accounts.value = data.items;
    total.value = data.total;
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false;
  }
}

// ---------- Form ----------
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const saving = ref(false);
const formRef = ref<FormInstance>();

const emptyForm = () => ({
  platform: "",
  account_name: "",
  username: "",
  password: "",
  api_key: "",
  cookie_data: "",
  expiration_date: null as string | null,
  notes: "",
});

const form = reactive(emptyForm());

const rules: FormRules = {
  platform: [{ required: true, message: "请选择平台", trigger: "change" }],
  account_name: [{ required: true, message: "请输入账号名称", trigger: "blur" }],
};

function resetForm() {
  editingId.value = null;
  Object.assign(form, emptyForm());
  formRef.value?.resetFields();
}

function openCreateDialog() {
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(row: AIAccount) {
  resetForm();
  editingId.value = row.id;
  form.platform = row.platform;
  form.account_name = row.account_name;
  form.expiration_date = row.expiration_date;
  form.notes = row.notes || "";
  // Sensitive fields are left blank on edit (they won't be updated unless filled)
  dialogVisible.value = true;
}

async function submitForm() {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  saving.value = true;
  try {
    const payload: any = {
      platform: form.platform,
      account_name: form.account_name,
      notes: form.notes || null,
      expiration_date: form.expiration_date || null,
    };
    // Only include sensitive fields if they were filled (for both create and update)
    if (form.username) payload.username = form.username;
    if (form.password) payload.password = form.password;
    if (form.api_key) payload.api_key = form.api_key;
    if (form.cookie_data) payload.cookie_data = form.cookie_data;

    if (editingId.value) {
      await accountsApi.update(editingId.value, payload);
      ElMessage.success("账号更新成功");
    } else {
      await accountsApi.create(payload);
      ElMessage.success("账号创建成功");
    }
    dialogVisible.value = false;
    fetchAccounts();
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

// ---------- Delete ----------
async function deleteAccount(row: AIAccount) {
  try {
    await ElMessageBox.confirm(
      `确定要删除账号「${row.account_name}」吗？此操作不可恢复。`,
      "确认删除",
      { type: "warning" }
    );
    await accountsApi.delete(row.id);
    ElMessage.success("账号已删除");
    fetchAccounts();
  } catch {
    // cancelled
  }
}

// ---------- Secret ----------
const secretVisible = ref(false);
const secretData = ref<AIAccountSecret | null>(null);

async function viewSecret(id: number) {
  try {
    const { data } = await accountsApi.getSecret(id);
    secretData.value = data;
    secretVisible.value = true;
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || "无权查看凭证");
  }
}

// ---------- Helpers ----------
function statusTagType(status: string) {
  const map: Record<string, string> = {
    active: "success",
    expired: "danger",
    error: "warning",
    suspended: "info",
  };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    active: "正常",
    expired: "已过期",
    error: "异常",
    suspended: "已停用",
  };
  return map[status] || status;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("zh-CN");
}

onMounted(fetchAccounts);
</script>

<style scoped>
.accounts-page {
  height: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
}
</style>
