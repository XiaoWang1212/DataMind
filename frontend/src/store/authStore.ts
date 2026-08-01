import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  type AuthUser,
} from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const isReady = ref(false)

  const isAuthenticated = computed(() => user.value !== null)

  async function checkSession (): Promise<void> {
    try {
      user.value = await fetchCurrentUser()
    } finally {
      isReady.value = true
    }
  }

  async function login (email: string, password: string): Promise<void> {
    await apiLogin(email, password)
    await checkSession()
  }

  async function register (email: string, password: string, displayName: string): Promise<void> {
    await apiRegister(email, password, displayName)
    await checkSession()
  }

  async function logout (): Promise<void> {
    await apiLogout()
    user.value = null
  }

  return { user, isReady, isAuthenticated, checkSession, login, register, logout }
})
