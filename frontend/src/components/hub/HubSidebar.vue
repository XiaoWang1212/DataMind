<template>
  <aside
    :class="[
      'hub-sidebar',
      `hub-sidebar--glass-${glassVariant}`,
      { 'hub-sidebar--collapsed': collapsed },
    ]"
  >
    <div aria-hidden="true" class="hub-sidebar-orbs">
      <div class="orb orb-2" />
      <div class="orb orb-3" />
    </div>

    <div class="hub-sidebar-header">
      <div class="hub-brand">
        <div class="hub-brand-title">DataMind</div>
        <div class="hub-brand-sub">框架分析系統</div>
      </div>
      <button class="hub-toggle-btn" @click="collapsed = !collapsed">
        <v-icon :icon="collapsed ? 'mdi-dock-right' : 'mdi-dock-left'" size="19" />
      </button>
    </div>

    <nav class="hub-nav" :style="{ '--active-index': Math.max(activeIndex, 0) }">
      <div
        aria-hidden="true"
        class="hub-nav-indicator"
        :class="{ 'hub-nav-indicator--hidden': activeIndex < 0 }"
      />

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

    <!-- 三塊包在一起淡出入，收合節奏才跟上面的區塊一致；
         整組移除也不會留下看不見卻仍可 Tab 到的登出鈕 -->
    <Transition name="hub-bottom">
      <div v-if="!collapsed" class="hub-sidebar-bottom">
        <div v-if="authStore.user" class="hub-sidebar-user">
          <div class="hub-user-name">{{ authStore.user.displayName || authStore.user.email }}</div>
          <button class="hub-logout-btn" title="登出" @click="handleLogout">
            <v-icon icon="mdi-logout" size="16" />
          </button>
        </div>

        <div class="hub-sidebar-footer">
          <div>版本 1.0.0</div>
          <div>© 2026 研究中心</div>
        </div>

        <button v-if="isDev" class="hub-glass-toggle" @click="toggleGlassVariant">
          玻璃：{{ glassVariant === 'light' ? '淺' : '深' }}
        </button>
      </div>
    </Transition>
  </aside>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { useDisplay } from 'vuetify'
  import { useAuthStore } from '@/store/authStore'

  const route = useRoute()
  const router = useRouter()
  const authStore = useAuthStore()

  // §8.3：小於 md(840px) 預設收合，主要是平板直向。斷點取自 vuetify.ts 的
  // mobileBreakpoint，收合後仍可手動展開
  const { mobile } = useDisplay()
  const collapsed = ref(mobile.value)

  watch(mobile, isMobile => {
    collapsed.value = isMobile
  })

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

  const activeIndex = computed(() => navItems.findIndex(item => route.path.startsWith(item.to)))
</script>

<style scoped>
.hub-sidebar {
  /* 版面基準值。收合後的各種置中位移都由這幾個推導，改一個不必手動重算其他 */
  --sidebar-width: 220px;
  --sidebar-width-collapsed: 72px;
  --sidebar-gutter: 16px;
  --nav-inset: 10px;
  --nav-item-height: 44px;
  --nav-item-inset: 12px;
  --nav-gap: 8px;
  --nav-icon-size: 22px; /* 對應 template 的 v-icon size */
  --toggle-size: 34px;

  /* 收合後把項目縮成正方形所需的左右內縮 */
  --collapsed-inset: calc(
    (var(--sidebar-width-collapsed) - var(--nav-inset) * 2 - var(--nav-item-height)) / 2
  );

  /* 深淺玻璃只有這幾個值不同，其餘規則共用。
     hover 是浮起（更亮的白）、選中是壓下去（帶藏青的凹陷），兩者互為反向 */
  --nav-fg: var(--color-ink-soft);
  /* 凹陷底色比原本的亮白底暗，墨色要再深一階才壓得住 */
  --nav-fg-strong: var(--color-ink-strong);
  --nav-surface-hover: rgba(255, 255, 255, 0.38);
  --nav-surface-active: rgba(14, 30, 66, 0.06);
  --nav-active-shadow:
    inset 0 1px 3px rgba(14, 30, 66, 0.18),
    inset 0 -1px 0 rgba(255, 255, 255, 0.7);
  --nav-border: var(--color-border);

  position: sticky;
  top: var(--sidebar-gutter);
  z-index: 2;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  /* dvh 而非 vh：平板瀏覽器網址列收合時 vh 會算進被遮住的那段，側邊欄會超出可視範圍 */
  height: calc(100dvh - var(--sidebar-gutter) * 2);
  /* 右邊不留：主內容自己的 padding 已經隔開了，再加一層會讓主內容左右留白不對稱 */
  margin: var(--sidebar-gutter) 0 var(--sidebar-gutter) var(--sidebar-gutter);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition: width var(--dur-base) var(--ease-in-out),
    min-width var(--dur-base) var(--ease-in-out);
}

.hub-sidebar--collapsed {
  width: var(--sidebar-width-collapsed);
  min-width: var(--sidebar-width-collapsed);
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
  /* 維持預設的靠左：品牌區永遠錨在最左，收合過程中文字才不會被剩餘空間推著跑 */
  gap: 8px;
  padding: 18px var(--nav-inset) 14px;
  transition: gap var(--dur-base) var(--ease-in-out);
}

/* 寬度交給 flex 由容器決定、自己 overflow 裁掉，收合展開時文字是被平滑裁切的。
   改用 opacity 淡出入的話會跟寬度轉場對不準，看起來就是閃一下 */
.hub-brand,
.hub-nav-label {
  min-width: 0;
  overflow: hidden;
}

/* 內距給文字本身而不是這層容器：容器縮到 0 的過程中文字位置才不會跟著往左跑 */
.hub-brand {
  flex: 1;
  transition: flex-grow var(--dur-base) var(--ease-in-out);
}

.hub-nav-label {
  flex: 1;
}

/* 收合後空間不足，不鎖住的話 flex 會從圖示身上扣寬度 */
.hub-nav-item .v-icon {
  flex-shrink: 0;
}

.hub-sidebar--collapsed .hub-sidebar-header {
  gap: 0;
}

.hub-sidebar--collapsed .hub-brand {
  flex-grow: 0;
}

.hub-nav-tooltip {
  position: absolute;
  left: 100%;
  top: 50%;
  z-index: 3;
  /* 壓進側邊欄內側，蓋過邊線但不吃到圖示 */
  margin-left: 4px;
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

/* 跟 nav 項目同一個內距，品牌文字左緣才對齊下方圖示 */
.hub-brand-title,
.hub-brand-sub {
  padding-left: var(--nav-item-inset);
}

.hub-brand-title {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.3;
  white-space: nowrap;
  background: linear-gradient(135deg, var(--color-ink) 0%, color-mix(in oklab, var(--color-ink) 55%, white) 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}

.hub-brand-sub {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--nav-fg);
  white-space: nowrap;
}

/* margin-left auto 讓按鈕靠右；收合後品牌區收到 0，改由 margin-right 把它拉回置中 */
.hub-toggle-btn {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: var(--toggle-size);
  height: var(--toggle-size);
  margin-top: 4px;
  margin-left: auto;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--nav-fg);
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    margin var(--dur-base) var(--ease-in-out);
}

/* translateX 是圖示視覺重心偏左的校正，不是版面需要 */
.hub-sidebar--collapsed .hub-toggle-btn {
  margin-right: calc(
    (var(--sidebar-width-collapsed) - var(--nav-inset) * 2 - var(--toggle-size)) / 2
  );
  transform: translateX(2px);
}

.hub-nav {
  --nav-pad-block: 6px;
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--nav-gap);
  padding: var(--nav-pad-block) var(--nav-inset);
}

/* 擺在項目之前，DOM 順序讓圖示與文字畫在它上面 */
.hub-nav-indicator {
  position: absolute;
  top: var(--nav-pad-block);
  left: var(--nav-inset);
  right: var(--nav-inset);
  height: var(--nav-item-height);
  border-radius: var(--radius-md);
  /* 上緣陰影、下緣亮線，光源由上往下（§4.3），看起來像刻進玻璃裡 */
  background: var(--nav-surface-active);
  box-shadow: var(--nav-active-shadow);
  transform: translateY(calc(var(--active-index) * (var(--nav-item-height) + var(--nav-gap))));
  /* left/right 要跟側邊欄寬度同一組時長，收合時才不會搶先跳到定位 */
  transition: transform var(--dur-base) var(--ease-in-out),
    left var(--dur-base) var(--ease-in-out),
    right var(--dur-base) var(--ease-in-out),
    opacity var(--dur-fast) var(--ease-out);
  pointer-events: none;
}

.hub-nav-indicator--hidden {
  opacity: 0;
}

.hub-sidebar--collapsed .hub-nav-indicator {
  left: calc(var(--nav-inset) + var(--collapsed-inset));
  right: calc(var(--nav-inset) + var(--collapsed-inset));
}

/* 高度直接吃 --nav-item-height，不靠 padding 加圖示高度湊出來——
   滑塊的位移量是用同一個變數算的，兩邊必須是同一個來源 */
.hub-nav-item {
  position: relative;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 14px;
  height: var(--nav-item-height);
  padding-inline: var(--nav-item-inset);
  border-radius: var(--radius-md);
  font-size: 13.5px;
  font-weight: 400;
  color: var(--nav-fg);
  text-decoration: none;
  white-space: nowrap;
  /* 底色要退得比滑塊快，點下去時才不會兩層白疊在一起 */
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-base) var(--ease-in-out),
    padding var(--dur-base) var(--ease-in-out),
    margin var(--dur-base) var(--ease-in-out);
}

/* 用 margin + padding 收成正方形，不用 margin:auto——auto 無法轉場，
   會在側邊欄還在收的時候就跳到定位 */
.hub-sidebar--collapsed .hub-nav-item {
  margin-inline: var(--collapsed-inset);
  padding-inline: calc((var(--nav-item-height) - var(--nav-icon-size)) / 2);
}

/* 底色交給 .hub-nav-indicator，這裡只管文字與圖示 */
.hub-nav-item--active {
  color: var(--nav-fg-strong);
  font-weight: 500;
}

.hub-sidebar-bottom {
  position: relative;
  z-index: 2;
}

.hub-bottom-enter-active,
.hub-bottom-leave-active {
  transition: opacity var(--dur-base) var(--ease-in-out);
}

.hub-bottom-enter-from,
.hub-bottom-leave-to {
  opacity: 0;
}

.hub-sidebar-user {
  position: relative;
  z-index: 2;
  display: flex;
  overflow: hidden;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid var(--nav-border);
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
  border: 1px solid var(--nav-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--nav-fg);
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
}

/* nowrap 擋掉換行造成的高度變化，overflow 再把溢出的部分裁掉——
   側邊欄本身為了 tooltip 不能裁切，只能各自處理 */
.hub-sidebar-footer {
  position: relative;
  z-index: 2;
  overflow: hidden;
  padding: 12px 14px;
  border-top: 1px solid var(--nav-border);
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--nav-fg);
  white-space: nowrap;
}

.hub-glass-toggle {
  position: relative;
  z-index: 2;
  display: block;
  overflow: hidden;
  margin: 0 14px 12px;
  padding: 4px 10px;
  white-space: nowrap;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 11px;
  color: var(--nav-fg);
  cursor: pointer;
}

/* hover 用白色半透明而不是不透明的灰混色：這是玻璃面板，蓋一層實色會讓它變濁。
   濃度取選中態的一半左右，兩者才是同一套語彙 */
@media (hover: hover) and (pointer: fine) {
  .hub-toggle-btn:hover,
  .hub-logout-btn:hover {
    background: var(--nav-surface-hover);
    color: var(--nav-fg-strong);
  }

  .hub-nav-item:hover {
    color: var(--nav-fg-strong);
  }

  /* 選中項底色由滑塊負責，再疊一層 hover 底色會在滑塊移動過程中互相打架 */
  .hub-nav-item:not(.hub-nav-item--active):hover {
    background: var(--nav-surface-hover);
  }

  .hub-nav-item:hover .hub-nav-tooltip {
    opacity: 1;
    transform: translateY(-50%) translateX(0) scale(1);
  }
}

/* ── 淺色玻璃（現行版本） ── */
.hub-sidebar--glass-light {
  background: rgba(255, 255, 255, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.55),
    inset 0 0 0 1px rgba(255, 255, 255, 0.35),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    var(--shadow-float);
}

/* ── 深色玻璃（§7.2 規範版本） ──
   只換上面那組語意變數，文字色、hover 底色、選中滑塊、分隔線都會跟著走 */
.hub-sidebar--glass-dark {
  --nav-fg: rgba(255, 255, 255, 0.72);
  --nav-fg-strong: #fff;
  --nav-surface-hover: rgba(255, 255, 255, 0.1);
  --nav-surface-active: rgba(0, 0, 0, 0.2);
  --nav-active-shadow:
    inset 0 1px 3px rgba(0, 0, 0, 0.34),
    inset 0 -1px 0 rgba(255, 255, 255, 0.12);
  --nav-border: rgba(255, 255, 255, 0.14);
  background: rgba(16, 32, 66, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: var(--shadow-float);
}

.hub-sidebar--glass-dark .hub-user-name {
  color: var(--nav-fg-strong);
}

.hub-sidebar--glass-dark .hub-brand-title {
  background: linear-gradient(135deg, #fff 0%, rgba(255, 255, 255, 0.62) 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}

.hub-sidebar--glass-dark .hub-logout-btn {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.12);
}

.hub-sidebar--glass-dark .hub-nav-tooltip {
  background: rgba(16, 32, 66, 0.92);
  color: var(--nav-fg-strong);
}

.hub-sidebar--glass-dark .hub-glass-toggle {
  border-color: rgba(255, 255, 255, 0.28);
}
</style>
