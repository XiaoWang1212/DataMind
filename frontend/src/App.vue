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

  // 在第一次繪製之前就定案，避免首屏先閃一下淺色再跳成深色
  themeStore.init()

  // 套用主題的唯一入口：store 只管狀態，換色統一在這裡發生
  watchEffect(() => {
    vuetifyTheme.change(themeStore.mode)
    // 下拉選單與引用浮卡是 Teleport 到 body 的，不在 .v-application 底下，
    // 拿不到掛在那裡的主題變數。class 同步到 <html>，整份文件才都吃得到
    const root = document.documentElement
    root.classList.toggle('v-theme--dark', themeStore.isDark)
    root.classList.toggle('v-theme--light', !themeStore.isDark)
  })
</script>
