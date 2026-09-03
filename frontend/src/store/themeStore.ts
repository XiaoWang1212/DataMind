import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'datamind:theme'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>('light')

  const isDark = computed(() => mode.value === 'dark')

  // localStorage 有值代表使用者親手選過，優先於系統偏好。
  // 不監聽系統偏好的後續變化：選過之後系統再變，不該蓋掉使用者的選擇
  function resolveInitialMode (): ThemeMode {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  function init (): void {
    mode.value = resolveInitialMode()
  }

  function toggle (): void {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
    localStorage.setItem(STORAGE_KEY, mode.value)
  }

  return { mode, isDark, init, toggle }
})
