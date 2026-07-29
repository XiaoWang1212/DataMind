<template>
  <div class="hub-wrap">
    <HubSidebar />

    <main class="hub-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import HubSidebar from '@/components/hub/HubSidebar.vue'
</script>

<style scoped>
.hub-wrap {
  display: flex;
  min-height: 100vh;
  background: var(--color-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color-scheme: light;
  color: var(--color-ink);
}

.hub-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 32px 36px;
}
</style>
