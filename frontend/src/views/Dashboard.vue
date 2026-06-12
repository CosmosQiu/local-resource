<template>
  <div class="dashboard">
    <!-- Overview Cards -->
    <el-row :gutter="20" class="overview-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ summary.total_accounts }}</div>
            <div class="stat-label">AI 账号总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value danger">{{ summary.expiring_accounts }}</div>
            <div class="stat-label">即将到期 (7天内)</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ summary.total_gpu_cards || '—' }}</div>
            <div class="stat-label">GPU 卡总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ summary.avg_gpu_utilization }}%</div>
            <div class="stat-label">GPU 平均利用率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- GPU Utilization Chart + Recent Requests -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>GPU 利用率趋势</template>
          <div ref="gpuChartRef" style="height: 350px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>最近申请</template>
          <el-timeline v-if="summary.recent_requests?.length">
            <el-timeline-item
              v-for="(item, idx) in summary.recent_requests"
              :key="idx"
              :timestamp="formatTime(item.time)"
              placement="top"
            >
              <strong>{{ item.user }}</strong>
              {{ item.type === 'container' ? '申请' : '申请裸金属' }}
              {{ item.gpu_count > 0 ? `${item.gpu_count}×GPU` : '' }}
              <el-tag size="small" :type="item.status === 'approved' ? 'success' : item.status === 'pending' ? 'warning' : 'info'">
                {{ item.status }}
              </el-tag>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无申请" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Fullscreen -->
    <div class="fullscreen-hint">
      <el-button type="primary" @click="enterFullscreen">
        <el-icon><FullScreen /></el-icon>
        全屏大屏模式
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { dashboardApi, type DashboardSummary } from "@/api/client";

const gpuChartRef = ref<HTMLElement>();

const summary = reactive<DashboardSummary>({
  total_accounts: 0,
  expiring_accounts: 0,
  total_gpu_cards: 0,
  avg_gpu_utilization: 0,
  recent_requests: [],
});

async function fetchSummary() {
  try {
    const { data } = await dashboardApi.summary();
    Object.assign(summary, data);
  } catch {
    // Silently fail — dashboard shows zeros
  }
}

function enterFullscreen() {
  document.documentElement.requestFullscreen();
}

function formatTime(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("zh-CN");
}

onMounted(() => {
  fetchSummary();
});
</script>

<style scoped>
.dashboard {
  height: 100%;
}

.overview-row {
  margin-bottom: 0;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #409eff;
}

.stat-value.danger {
  color: #f56c6c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.fullscreen-hint {
  margin-top: 20px;
  text-align: right;
}
</style>
