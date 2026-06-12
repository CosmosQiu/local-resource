import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/api/client";
import router from "@/router";

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  display_name: string | null;
  department: string | null;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
  permissions: string[];
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserInfo | null>(null);
  const accessToken = ref<string | null>(localStorage.getItem("access_token"));
  const refreshToken = ref<string | null>(localStorage.getItem("refresh_token"));

  const isLoggedIn = computed(() => !!accessToken.value);

  function hasPermission(perm: string): boolean {
    if (!user.value) return false;
    if (user.value.is_superuser) return true;
    return user.value.permissions.includes(perm);
  }

  async function login(username: string, password: string) {
    const { data } = await authApi.login(username, password);
    accessToken.value = data.access_token;
    refreshToken.value = data.refresh_token;
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    await fetchUser();
  }

  async function fetchUser() {
    try {
      const { data } = await authApi.me();
      user.value = data;
    } catch {
      logout();
    }
  }

  function logout() {
    user.value = null;
    accessToken.value = null;
    refreshToken.value = null;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/login");
  }

  return {
    user,
    accessToken,
    refreshToken,
    isLoggedIn,
    hasPermission,
    login,
    fetchUser,
    logout,
  };
});
