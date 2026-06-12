import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("@/views/Layout.vue"),
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/Dashboard.vue"),
        meta: { title: "大屏监控" },
      },
      {
        path: "accounts",
        name: "Accounts",
        component: () => import("@/views/Accounts.vue"),
        meta: { title: "AI 账号管理", permission: "accounts.read" },
      },
      {
        path: "compute",
        name: "Compute",
        component: () => import("@/views/Compute.vue"),
        meta: { title: "算力资源", permission: "compute.read" },
      },
      {
        path: "requests",
        name: "Requests",
        component: () => import("@/views/Requests.vue"),
        meta: { title: "申请管理", permission: "compute.request" },
      },
      {
        path: "admin",
        name: "Admin",
        component: () => import("@/views/Admin.vue"),
        meta: { title: "系统管理", permission: "admin.manage_users" },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation guard — check auth
router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem("access_token");

  if (to.meta.public) {
    // Already logged in → redirect to dashboard
    if (token && to.name === "Login") {
      return next("/dashboard");
    }
    return next();
  }

  if (!token) {
    return next("/login");
  }

  // Permission check
  if (to.meta.permission) {
    try {
      const { useAuthStore } = await import("@/stores/auth");
      const auth = useAuthStore();
      if (!auth.user) {
        await auth.fetchUser();
      }
      if (!auth.hasPermission(to.meta.permission as string)) {
        return next("/dashboard");
      }
    } catch {
      return next("/login");
    }
  }

  next();
});

export default router;
