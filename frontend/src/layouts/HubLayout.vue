<template>
  <div class="hub-wrap">
    <HubSidebar />

    <div aria-hidden="true" class="hub-glass-orbs">
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
    </div>

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

.hub-glass-orbs {
  position: fixed;
  top: 0;
  left: 0;
  width: 210px;
  height: 100vh;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
  transition: width 0.2s ease;
}

.hub-sidebar--collapsed ~ .hub-glass-orbs {
  width: 56px;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(38px);
}

.orb-1 {
  width: 160px;
  height: 160px;
  top: -40px;
  left: -30px;
  background: radial-gradient(circle, var(--color-accent) 0%, transparent 70%);
  opacity: 0.55;
}

.orb-2 {
  width: 130px;
  height: 130px;
  top: 260px;
  left: 40px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-accent) 60%, white) 0%, transparent 70%);
  opacity: 0.5;
}

.orb-3 {
  width: 110px;
  height: 110px;
  top: 480px;
  left: -20px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-accent) 85%, black) 0%, transparent 70%);
  opacity: 0.35;
}

.hub-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 32px 36px;
}
</style>
