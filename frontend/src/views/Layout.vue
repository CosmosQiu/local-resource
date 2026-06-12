<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
      <div class="logo">
        <span v-if="!isCollapse">AI Resource Hub</span>
        <span v-else class="logo-mini">ARH</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#1a1a2e"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>大屏监控</span>
        </el-menu-item>
        <el-menu-item
          v-if="auth.hasPermission('accounts.read')"
          index="/accounts"
        >
          <el-icon><UserFilled /></el-icon>
          <span>AI 账号管理</span>
        </el-menu-item>
        <el-menu-item
          v-if="auth.hasPermission('compute.read')"
          index="/compute"
        >
          <el-icon><Cpu /></el-icon>
          <span>算力资源</span>
        </el-menu-item>
        <el-menu-item
          v-if="auth.hasPermission('compute.request')"
          index="/requests"
        >
          <el-icon><Document /></el-icon>
          <span>申请管理</span>
        </el-menu-item>
        <el-menu-item
          v-if="auth.hasPermission('admin.manage_users')"
          index="/admin"
        >
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main -->
    <el-container>
      <!-- Header -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-button
            text
            @click="isCollapse = !isCollapse"
          >
            <el-icon><Fold v-if="!isCollapse" /><Expand v-else /></el-icon>
          </el-button>
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <span class="user-name">{{ auth.user?.display_name || auth.user?.username }}</span>
          <el-dropdown>
            <el-avatar :size="32" icon="UserFilled" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const auth = useAuthStore();
const isCollapse = ref(false);

const activeMenu = computed(() => route.path);
const currentTitle = computed(() => route.meta?.title as string || "");

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchUser();
  }
});

function handleLogout() {
  auth.logout();
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-aside {
  background-color: #1a1a2e;
  overflow-x: hidden;
  transition: width 0.3s;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-mini {
  font-size: 14px;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-name {
  font-size: 14px;
  color: #606266;
}

.layout-main {
  background: #f0f2f5;
  padding: 20px;
}
</style>
