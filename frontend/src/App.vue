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
  watchEffect(() => vuetifyTheme.change(themeStore.mode))
</script>
