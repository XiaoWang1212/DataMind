<template>
  <div
    v-if="visible"
    class="code-preview-backdrop"
    @click.self="emit('close')"
  >
    <div class="code-preview-card">
      <header class="code-preview-header">
        <input
          v-model="filename"
          class="code-preview-filename-input"
          spellcheck="false"
          type="text"
        >
        <div class="code-preview-actions">
          <AppButton variant="ghost" @click="handleCopy">
            <v-icon :icon="copyError ? 'mdi-alert-circle-outline' : (copied ? 'mdi-check' : 'mdi-content-copy')" size="15" />
            {{ copyError ? '複製失敗' : (copied ? '已複製' : '複製') }}
          </AppButton>
          <AppButton variant="primary" @click="handleDownload">
            <v-icon icon="mdi-download" size="15" />
            下載
          </AppButton>
          <AppButton icon-only title="關閉" variant="ghost" @click="emit('close')">
            <v-icon icon="mdi-close" size="16" />
          </AppButton>
        </div>
      </header>

      <pre class="code-preview-body" :style="codeBodyStyle"><code class="language-python" v-html="highlightedCode" /></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
  import hljs from 'highlight.js/lib/core'
  import python from 'highlight.js/lib/languages/python'
  // 兩份主題都用 ?raw 匯入成純文字字串，不會像一般 CSS import 那樣直接套用到全站——
  // 實際要套用哪一份，由下面的 <style> 依目前 light/dark 模式動態決定
  import darkThemeCss from 'highlight.js/styles/atom-one-dark.css?raw'
  import lightThemeCss from 'highlight.js/styles/atom-one-light.css?raw'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import { useThemeStore } from '@/store/themeStore'

  hljs.registerLanguage('python', python)

  const themeStore = useThemeStore()
  const highlightThemeCss = computed(() => themeStore.isDark ? darkThemeCss : lightThemeCss)
  // atom-one-dark / atom-one-light 兩份主題各自的底色跟基礎文字色，主題檔本身沒有用 CSS 變數，
  // 沒辦法只換主題檔就連底色一起換，所以這裡跟著手動對應
  const codeBodyStyle = computed(() => themeStore.isDark
    ? { background: '#282c34', color: '#abb2bf' }
    : { background: '#fafafa', color: '#383a42' })

  // Vue 的 SFC 編譯器不允許在 <template> 裡直接寫 <style>（會被當成側效應標籤忽略、直接編譯失敗），
  // 所以要動態切換 highlight.js 主題只能用原生 DOM API 手動管理一個 <style> 節點，
  // 不能宣告在 template 裡。掛在 document.head 上（不是這個元件自己的節點），
  // 因為 highlight.js 輸出的 .hljs-* 是全站唯一一份、不會跟其他樣式衝突
  let highlightStyleEl: HTMLStyleElement | null = null

  watch(highlightThemeCss, css => {
    if (!highlightStyleEl) {
      highlightStyleEl = document.createElement('style')
      document.head.appendChild(highlightStyleEl)
    }
    highlightStyleEl.textContent = css
  }, { immediate: true })

  const props = defineProps<{
    visible: boolean
    code: string
    defaultFilename: string
  }>()

  const emit = defineEmits<{
    close: []
  }>()

  const filename = ref(props.defaultFilename)
  const copied = ref(false)
  const copyError = ref(false)

  // highlight.js 直接對純文字做語法高亮、輸出 HTML 字串，比操作 DOM 節點（highlightElement）
  // 更適合搭配 Vue 的響應式渲染——code 換了 computed 會自動重新算，不用自己在 watch 裡手動觸發
  const highlightedCode = computed(() => hljs.highlight(props.code, { language: 'python' }).value)

  // 每次重新打開彈窗都重置檔名輸入框，避免上次編輯的殘留值蓋過新產生的預設檔名
  watch(() => props.visible, visible => {
    if (visible) {
      filename.value = props.defaultFilename
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  }, { immediate: true })

  function onKeydown (event: KeyboardEvent): void {
    if (event.key === 'Escape') emit('close')
  }

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown)
    highlightStyleEl?.remove()
  })

  async function handleCopy (): Promise<void> {
    try {
      await navigator.clipboard.writeText(props.code)
      copyError.value = false
      copied.value = true
      setTimeout(() => { copied.value = false }, 2000)
    } catch {
      copied.value = false
      copyError.value = true
      setTimeout(() => { copyError.value = false }, 2000)
    }
  }

  function resolveFilename (): string {
    const trimmed = filename.value.trim()
    if (!trimmed) return props.defaultFilename
    return trimmed.toLowerCase().endsWith('.py') ? trimmed : `${trimmed}.py`
  }

  function handleDownload (): void {
    const blob = new Blob([props.code], { type: 'text/x-python' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = resolveFilename()
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }
</script>

<style scoped>
  .code-preview-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(18, 30, 58, 0.45);
    z-index: 1000;
  }

  .code-preview-card {
    display: flex;
    width: 780px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    flex-direction: column;
    overflow: hidden;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-float);
  }

  .code-preview-header {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--color-border);
  }

  .code-preview-filename-input {
    flex: 1;
    min-width: 0;
    padding: 5px 8px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    outline: none;
    background: transparent;
    color: var(--color-text);
    font-family: var(--font-heading);
    font-size: 15px;
    font-weight: 500;
    transition: background-color var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out);
  }

  .code-preview-filename-input:hover {
    background: color-mix(in oklab, var(--color-ink) 6%, var(--color-surface));
  }

  .code-preview-filename-input:focus {
    border-color: var(--color-border-strong);
    background: var(--color-surface);
  }

  .code-preview-actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 6px;
  }

  .code-preview-body {
    flex: 1;
    margin: 0;
    overflow: auto;
    padding: 16px 20px;
    font-family: var(--font-mono, 'SF Mono', Consolas, monospace);
    font-size: 13px;
    line-height: 1.6;
  }
</style>
