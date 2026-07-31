<template>
  <aside :class="['hub-sidebar', { 'hub-sidebar--collapsed': collapsed }]">
    <div class="hub-sidebar-header">
      <div v-if="!collapsed" class="hub-brand">
        <div class="hub-brand-title">研究中心</div>
        <div class="hub-brand-sub">框架分析系統</div>
      </div>
      <button class="hub-toggle-btn" @click="collapsed = !collapsed">
        <v-icon :icon="collapsed ? 'mdi-chevron-right' : 'mdi-chevron-left'" size="15" />
      </button>
    </div>

    <nav class="hub-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="hub-nav-item"
        :class="{ 'hub-nav-item--active': route.path.startsWith(item.to) }"
      >
        <v-icon :icon="item.icon" size="19" />
        <span v-if="!collapsed" class="hub-nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div v-if="!collapsed" class="hub-sidebar-footer">
      <div>版本 1.0.0</div>
      <div>© 2026 研究中心</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'

const route = useRoute()
const collapsed = ref(false)

const navItems = [
  { to: '/hub/dashboard', icon: 'mdi-home-outline', label: '儀表板' },
  { to: '/hub/library', icon: 'mdi-book-open-outline', label: '框架庫' },
  { to: '/hub/projects', icon: 'mdi-folder-outline', label: '專案' },
  { to: '/hub/settings', icon: 'mdi-cog-outline', label: '設定' },
]
</script>

<style scoped>
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-top: 1.5px solid rgba(255, 255, 255, 0.9);
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.55),
    inset 0 0 0 1px rgba(255, 255, 255, 0.35),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    4px 0 24px rgba(28, 33, 48, 0.1);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 2;
}

.hub-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 70%;
  height: 220%;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 255, 255, 0.7) 50%, transparent 65%);
  transform: translate(-160%, -20%) rotate(12deg);
  animation: hub-sidebar-shine 4.5s ease-in-out infinite;
  pointer-events: none;
  z-index: 1;
}

.hub-sidebar--collapsed {
  width: 56px;
  min-width: 56px;
}

.hub-sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 14px 14px;
  gap: 8px;
  position: relative;
  z-index: 2;
}

.hub-brand {
  overflow: hidden;
  flex: 1;
}

.hub-brand-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--color-ink);
  white-space: nowrap;
  line-height: 1.3;
}

.hub-brand-sub {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 3px;
  white-space: nowrap;
  line-height: 1.4;
}

.hub-toggle-btn {
  width: 22px;
  height: 22px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #9ca3af;
  transition: background 0.15s;
  margin-top: 2px;
}

.hub-toggle-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.hub-nav {
  flex: 1;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  position: relative;
  z-index: 2;
}

.hub-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 7px;
  text-decoration: none;
  color: var(--color-secondary);
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.12s;
  white-space: nowrap;
}

.hub-nav-item:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.hub-nav-item--active {
  background: var(--color-accent);
  color: var(--color-ink);
}

.hub-nav-label {
  overflow: hidden;
}

.hub-sidebar-footer {
  padding: 12px 14px;
  font-size: 10.5px;
  color: #9ca3af;
  line-height: 1.7;
  border-top: 1px solid #f0f0f0;
  position: relative;
  z-index: 2;
}

@keyframes hub-sidebar-shine {
  0%, 25% {
    transform: translate(-160%, -20%) rotate(12deg);
  }
  65%, 100% {
    transform: translate(160%, -20%) rotate(12deg);
  }
}
</style>
