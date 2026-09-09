<template>
  <v-app>
    <v-main>
      <RouterView />
    </v-main>
  </v-app>
</template>

<script lang="ts" setup>
  import { watchEffect } from 'vue'
  import { RouterView } from 'vue-router'
  import { useTheme } from 'vuetify'
  import { useThemeStore } from '@/store/themeStore'

  const themeStore = useThemeStore()
  const vuetifyTheme = useTheme()

  // 讀 localStorage / 系統偏好定出初值。首次繪製前的防閃爍由 index.html 的 inline
  // script 負責，這裡是同一份判斷在 Vue 這側的權威版本
  themeStore.init()

  // 套用主題的唯一入口：store 只管狀態，換色統一在這裡發生
  watchEffect(() => {
    vuetifyTheme.change(themeStore.mode)
    // Vuetify 自己的 --v-theme-* 是發在 :root 上的，但專案的 .v-theme--dark {} 區塊
    // （glass.css、main.scss、元件內）掛在 .v-application。下拉選單與引用浮卡是
    // Teleport 到 body 的，落在那個範圍外，class 要同步到 <html> 才吃得到
    const root = document.documentElement
    root.classList.toggle('v-theme--dark', themeStore.isDark)
    root.classList.toggle('v-theme--light', !themeStore.isDark)
    // 捲軸、原生 select 這些由瀏覽器繪製的元件只吃 color-scheme。index.html 的
    // inline script 只在載入時設一次，切換主題時要在這裡跟著更新，否則它們會
    // 停在開啟頁面當下的配色，重新整理才變
    root.style.colorScheme = themeStore.isDark ? 'dark' : 'light'
  })
</script>
