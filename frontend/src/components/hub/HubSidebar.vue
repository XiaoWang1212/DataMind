<template>
  <aside
    :class="[
      'hub-sidebar',
      `hub-sidebar--glass-${glassVariant}`,
      { 'hub-sidebar--collapsed': collapsed },
    ]"
  >
    <div aria-hidden="true" class="hub-sidebar-orbs">
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
    </div>

    <div class="hub-sidebar-header">
      <div class="hub-brand">
        <div class="hub-brand-title">DataMind</div>
        <div class="hub-brand-sub">框架分析系統</div>
      </div>
      <button class="hub-toggle-btn" @click="collapsed = !collapsed">
        <v-icon :icon="collapsed ? 'mdi-dock-right' : 'mdi-dock-left'" size="15" />
      </button>
    </div>

    <nav class="hub-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        class="hub-nav-item"
        :class="{ 'hub-nav-item--active': route.path.startsWith(item.to) }"
        :to="item.to"
      >
        <v-icon :icon="item.icon" size="22" />
        <span class="hub-nav-label">{{ item.label }}</span>
        <span v-if="collapsed" aria-hidden="true" class="hub-nav-tooltip glass-menu">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- 底部兩區塊在水平收合時不會被寬度切到，直接移除比淡出乾淨，
         也不會留下看不見卻仍可 Tab 到的登出鈕 -->
    <div v-if="!collapsed && authStore.user" class="hub-sidebar-user">
      <div class="hub-user-name">{{ authStore.user.displayName || authStore.user.email }}</div>
      <button class="hub-logout-btn" title="登出" @click="handleLogout">
        <v-icon icon="mdi-logout" size="16" />
      </button>
    </div>

    <div v-if="!collapsed" class="hub-sidebar-footer">
      <div>版本 1.0.0</div>
      <div>© 2026 研究中心</div>
    </div>

    <button v-if="isDev && !collapsed" class="hub-glass-toggle" @click="toggleGlassVariant">
      玻璃：{{ glassVariant === 'light' ? '淺' : '深' }}
    </button>
  </aside>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { useAuthStore } from '@/store/authStore'

  const route = useRoute()
  const router = useRouter()
  const authStore = useAuthStore()
  const collapsed = ref(false)

  const GLASS_STORAGE_KEY = 'datamind:sidebar-glass'

  // 深/淺兩版玻璃並存只是為了在瀏覽器互相對照，定案後刪掉落選的那版與這個切換
  const glassVariant = ref<'light' | 'dark'>(
    (localStorage.getItem(GLASS_STORAGE_KEY) as 'light' | 'dark' | null) ?? 'light',
  )
  const isDev = import.meta.env.DEV

  function toggleGlassVariant (): void {
    glassVariant.value = glassVariant.value === 'light' ? 'dark' : 'light'
    localStorage.setItem(GLASS_STORAGE_KEY, glassVariant.value)
  }

  async function handleLogout (): Promise<void> {
    try {
      await authStore.logout()
    } catch {
      // even if the logout request failed, don't leave the user stuck on this page
    }
    router.push('/login')
  }

  const navItems = [
    { to: '/hub/dashboard', icon: 'mdi-home-outline', label: '儀表板' },
    { to: '/hub/library', icon: 'mdi-book-open-outline', label: '框架庫' },
    { to: '/hub/projects', icon: 'mdi-folder-outline', label: '專案' },
    { to: '/hub/settings', icon: 'mdi-cog-outline', label: '設定' },
  ]
</script>

<style scoped>
.hub-sidebar {
  position: sticky;
  top: 16px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  width: 220px;
  min-width: 220px;
  height: calc(100vh - 32px);
  margin: 16px;
  border-radius: var(--radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition: width var(--dur-base) var(--ease-in-out),
    min-width var(--dur-base) var(--ease-in-out);
}

.hub-sidebar--collapsed {
  width: 72px;
  min-width: 72px;
}

.hub-sidebar-orbs {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(38px);
}

.orb-1 {
  top: -40px;
  left: -30px;
  width: 160px;
  height: 160px;
  background: radial-gradient(circle, var(--color-ink) 0%, transparent 70%);
  opacity: 0.55;
}

.orb-2 {
  top: 260px;
  left: 40px;
  width: 130px;
  height: 130px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-ink) 60%, white) 0%, transparent 70%);
  opacity: 0.5;
}

.orb-3 {
  top: 480px;
  left: -20px;
  width: 110px;
  height: 110px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-ink) 85%, black) 0%, transparent 70%);
  opacity: 0.35;
}

.hub-sidebar-header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 18px 10px 14px;
}

/* 收合時文字先淡出、寬度再收，避免文字被寬度轉場硬切 */
.hub-brand,
.hub-nav-label {
  overflow: hidden;
  transition: opacity var(--dur-fast) var(--ease-out);
}

.hub-brand {
  flex: 1;
}

.hub-sidebar--collapsed .hub-brand,
.hub-sidebar--collapsed .hub-nav-label {
  opacity: 0;
}

.hub-nav-tooltip {
  position: absolute;
  left: 100%;
  top: 50%;
  z-index: 3;
  margin-left: 10px;
  padding: 6px 10px;
  color: var(--color-text);
  font-size: 12.5px;
  font-weight: 400;
  white-space: nowrap;
  opacity: 0;
  transform: translateY(-50%) translateX(-4px) scale(0.97);
  transition: opacity var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
  pointer-events: none;
}

.hub-brand-title {
  font-size: 14.5px;
  font-weight: 500;
  line-height: 1.3;
  color: var(--color-text);
  white-space: nowrap;
}

.hub-brand-sub {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-ink-soft);
  white-space: nowrap;
}

.hub-toggle-btn {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-top: 2px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink-soft);
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out);
}

.hub-nav {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1px;
  padding: 6px 10px;
}

.hub-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-weight: 400;
  color: var(--color-ink-soft);
  text-decoration: none;
  white-space: nowrap;
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    padding var(--dur-base) var(--ease-in-out);
}

/* 收合後把圖示推到 72px 寬度的中間 */
.hub-sidebar--collapsed .hub-nav-item {
  padding-inline: 15px;
}

.hub-nav-item--active {
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-ink);
  font-weight: 500;
}

.hub-sidebar-user {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid var(--color-border);
}

.hub-user-name {
  overflow: hidden;
  font-size: 12.5px;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hub-logout-btn {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink-soft);
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
}

.hub-sidebar-footer {
  position: relative;
  z-index: 2;
  padding: 12px 14px;
  border-top: 1px solid var(--color-border);
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--color-ink-soft);
}

.hub-glass-toggle {
  position: relative;
  z-index: 2;
  margin: 0 14px 12px;
  padding: 4px 10px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 11px;
  color: var(--color-ink-soft);
  cursor: pointer;
}

/* hover 用白色半透明而不是不透明的灰混色：這是玻璃面板，蓋一層實色會讓它變濁。
   濃度取選中態（0.72）的一半左右，兩者才是同一套語彙 */
@media (hover: hover) and (pointer: fine) {
  .hub-toggle-btn:hover,
  .hub-nav-item:hover {
    background: rgba(255, 255, 255, 0.38);
  }

  .hub-logout-btn:hover {
    background: rgba(255, 255, 255, 0.38);
    color: var(--color-text);
  }

  .hub-nav-item:hover .hub-nav-tooltip {
    opacity: 1;
    transform: translateY(-50%) translateX(0) scale(1);
  }
}

/* ── 淺色玻璃（現行版本） ── */
.hub-sidebar--glass-light {
  background: rgba(255, 255, 255, 0.42);
  border: 1.5px solid rgba(255, 255, 255, 0.9);
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.55),
    inset 0 0 0 1px rgba(255, 255, 255, 0.35),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    var(--shadow-float);
}

/* ── 深色玻璃（§7.2 規範版本） ── */
.hub-sidebar--glass-dark {
  background: rgba(16, 32, 66, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: var(--shadow-float);
}

.hub-sidebar--glass-dark .hub-brand-title,
.hub-sidebar--glass-dark .hub-user-name {
  color: #fff;
}

.hub-sidebar--glass-dark .hub-brand-sub,
.hub-sidebar--glass-dark .hub-nav-item,
.hub-sidebar--glass-dark .hub-sidebar-footer,
.hub-sidebar--glass-dark .hub-glass-toggle {
  color: rgba(255, 255, 255, 0.72);
}

.hub-sidebar--glass-dark .hub-nav-item--active {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.hub-sidebar--glass-dark .hub-toggle-btn,
.hub-sidebar--glass-dark .hub-logout-btn {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
}

.hub-sidebar--glass-dark .hub-nav-tooltip {
  background: rgba(16, 32, 66, 0.92);
  color: #fff;
}

.hub-sidebar--glass-dark .hub-sidebar-user,
.hub-sidebar--glass-dark .hub-sidebar-footer {
  border-top-color: rgba(255, 255, 255, 0.14);
}

.hub-sidebar--glass-dark .hub-glass-toggle {
  border-color: rgba(255, 255, 255, 0.28);
}

@media (hover: hover) and (pointer: fine) {
  .hub-sidebar--glass-dark .hub-toggle-btn:hover,
  .hub-sidebar--glass-dark .hub-nav-item:hover,
  .hub-sidebar--glass-dark .hub-logout-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
}
</style>
