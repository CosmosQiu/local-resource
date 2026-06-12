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
            <div class="stat-value">{{ summary.total_hosts }}</div>
            <div class="stat-label">监控主机数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ onlineHosts }} / {{ summary.total_hosts }}</div>
            <div class="stat-label">在线 / 总数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Real-time Resource Charts -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span style="font-weight:bold">CPU 使用率 (%)</span></template>
          <div ref="cpuChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span style="font-weight:bold">内存使用率 (%)</span></template>
          <div ref="memChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span style="font-weight:bold">磁盘使用率 (%)</span></template>
          <div ref="diskChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Running Resources -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span style="display:flex;align-items:center;gap:8px">
              <span style="font-weight:bold">运行中资源</span>
              <el-tag v-if="runningResources.length" size="small" type="success">{{ runningResources.length }} 个运行中</el-tag>
            </span>
          </template>
          <el-table v-if="runningResources.length" :data="runningResources" size="small">
            <el-table-column prop="username" label="用户" width="80" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">{{ row.request_type === 'container' ? '容器' : '裸金属' }}</template>
            </el-table-column>
            <el-table-column label="规格" width="160">
              <template #default="{ row }">{{ row.cpu_cores }}C / {{ row.memory_gb }}G / {{ row.disk_gb }}G{{ row.gpu_count > 0 ? ` / ${row.gpu_count}×GPU` : '' }}</template>
            </el-table-column>
            <el-table-column label="连接地址" min-width="200">
              <template #default="{ row }">
                <el-link v-if="row.access_url" :underline="false" style="font-family:monospace;font-size:12px">
                  ssh root@{{ row.access_url }}
                </el-link>
                <span v-else style="color:#909399">—</span>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无运行中资源" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent Requests -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
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
              {{ item.type === 'container' ? '申请容器' : '申请裸金属' }}
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
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from "vue";
import * as echarts from "echarts";
import { dashboardApi, requestsApi, type DashboardSummary, type HostMetrics, type ContainerRequest } from "@/api/client";

// ---------- Data ----------
const cpuChartRef = ref<HTMLElement>();
const memChartRef = ref<HTMLElement>();
const diskChartRef = ref<HTMLElement>();

const summary = reactive<DashboardSummary>({
  total_accounts: 0,
  expiring_accounts: 0,
  total_hosts: 0,
  hosts: [],
  recent_requests: [],
});

const runningResources = ref<ContainerRequest[]>([]);

const onlineHosts = computed(() => summary.hosts.filter(h => h.status === "online").length);

// Historical data for real-time curves
const MAX_HISTORY = 30;
const history = reactive<{
  timestamps: string[];
  cpu: Record<string, number[]>;
  memory: Record<string, number[]>;
  disk: Record<string, number[]>;
}>({ timestamps: [], cpu: {}, memory: {}, disk: {} });

// ---------- Charts ----------
let cpuChart: echarts.ECharts | null = null;
let memChart: echarts.ECharts | null = null;
let diskChart: echarts.ECharts | null = null;

function makeChartOption(
  hosts: HostMetrics[],
  metricKey: "cpu_percent" | "memory_percent" | "disk_percent",
  color: string,
): echarts.EChartsOption {
  const series = hosts.map((h) => {
    const key = `${h.host_name} (${h.host_ip})`;
    const data = history[metricKey === "cpu_percent" ? "cpu" : metricKey === "memory_percent" ? "memory" : "disk"][key] || [];
    return {
      name: key,
      type: "line" as const,
      data: data,
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.1 },
    };
  });

  return {
    tooltip: { trigger: "axis" as const },
    legend: {
      data: hosts.map(h => `${h.host_name} (${h.host_ip})`),
      bottom: 0,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 50, right: 20, top: 10, bottom: 40 },
    xAxis: {
      type: "category" as const,
      data: history.timestamps,
      axisLabel: { fontSize: 10, rotate: 30 },
    },
    yAxis: {
      type: "value" as const,
      min: 0,
      max: 100,
      axisLabel: { formatter: "{value}%" },
    },
    series,
    color: hosts.map((_, i) => {
      const colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#fc8452"];
      return colors[i % colors.length];
    }),
  };
}

function initCharts() {
  if (cpuChartRef.value) {
    cpuChart = echarts.init(cpuChartRef.value);
  }
  if (memChartRef.value) {
    memChart = echarts.init(memChartRef.value);
  }
  if (diskChartRef.value) {
    diskChart = echarts.init(diskChartRef.value);
  }
}

function updateCharts() {
  const hosts = summary.hosts || [];
  if (!hosts.length) return;

  if (cpuChart) cpuChart.setOption(makeChartOption(hosts, "cpu_percent", "#5470c6"), true);
  if (memChart) memChart.setOption(makeChartOption(hosts, "memory_percent", "#91cc75"), true);
  if (diskChart) diskChart.setOption(makeChartOption(hosts, "disk_percent", "#fac858"), true);
}

// ---------- Data fetching ----------
async function fetchSummary() {
  try {
    const { data } = await dashboardApi.summary();
    Object.assign(summary, data);

    // Append to history
    const now = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    history.timestamps.push(now);
    if (history.timestamps.length > MAX_HISTORY) history.timestamps.shift();

    for (const host of summary.hosts) {
      const key = `${host.host_name} (${host.host_ip})`;
      for (const metric of ["cpu", "memory", "disk"] as const) {
        if (!history[metric][key]) history[metric][key] = [];
        const val = metric === "cpu" ? host.cpu_percent : metric === "memory" ? host.memory_percent : host.disk_percent;
        history[metric][key].push(val);
        if (history[metric][key].length > MAX_HISTORY) history[metric][key].shift();
      }
    }

    updateCharts();
  } catch {
    // Silently fail — dashboard shows zeros
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

// ---------- Lifecycle ----------
function enterFullscreen() {
  document.documentElement.requestFullscreen();
}

function formatTime(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("zh-CN");
}

async function fetchRunningResources() {
  try {
    const { data } = await requestsApi.list({ status: "running" });
    runningResources.value = data.items || [];
  } catch { /* silently fail */ }
}

onMounted(async () => {
  await nextTick();
  initCharts();
  await Promise.all([fetchSummary(), fetchRunningResources()]);
  pollTimer = setInterval(() => { fetchSummary(); fetchRunningResources(); }, 30000);
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  window.removeEventListener("resize", handleResize);
  cpuChart?.dispose();
  memChart?.dispose();
  diskChart?.dispose();
});

function handleResize() {
  cpuChart?.resize();
  memChart?.resize();
  diskChart?.resize();
}
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
