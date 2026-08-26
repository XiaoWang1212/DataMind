<template>
  <aside class="mapping-chat glass-panel">
    <div class="chat-head">
      <div class="chat-head-icon">
        <v-icon icon="mdi-chat-processing-outline" size="18" />
      </div>
      <span>AI 助理</span>
    </div>

    <div v-if="loading" class="chat-offline">
      AI 助理需等待欄位對應結果產生後才能使用。
    </div>
    <div v-else-if="!available" class="chat-offline">
      AI 建議暫時無法使用，可用左側下拉選單手動對應。
    </div>

    <div ref="scrollRef" class="chat-body">
      <div v-if="!loading && available" class="chat-bubble chat-bubble--assistant chat-bubble--opener">
        {{ CHAT_OPENER }}
      </div>
      <!-- enter-rise 掛在氣泡本身：每則訊息是一個新元素，動畫只會跑一次 -->
      <div
        v-for="(message, i) in history"
        :key="i"
        class="chat-bubble enter-rise"
        :class="`chat-bubble--${message.role}`"
        v-html="renderChatText(message.content)"
      />
      <div v-if="pending" class="chat-bubble chat-bubble--assistant chat-bubble--pending enter-rise">
        思考中…
      </div>
    </div>

    <form class="chat-input" @submit.prevent="submit">
      <textarea
        ref="fieldRef"
        v-model="draft"
        class="chat-field"
        :disabled="!available || pending"
        placeholder="例如：Braden 分數是 braden_total"
        rows="1"
        @input="autoGrow"
        @keydown="onFieldKeydown"
      />
      <AppButton
        class="chat-send"
        :disabled="!available || pending || !draft.trim()"
        type="submit"
      >
        送出
      </AppButton>
    </form>
  </aside>
</template>

<script setup lang="ts">
  import type { ChatMessage } from '@/types/fieldMapping'
  import { nextTick, ref, watch } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import { renderChatText } from '@/utils/formatChatText'

  const props = defineProps<{
    history: ChatMessage[]
    pending: boolean
    available: boolean
    loading: boolean
  }>()

  const emit = defineEmits<{
    send: [message: string]
  }>()

  // 開場白不進 history，不存草稿
  const CHAT_OPENER = '我可以協助調整左側的欄位對應，請直接以文字說明您的需求，'
    + '例如「年齡對應到 pt_age」或「BMI 這一欄資料表中沒有」。'

  // 約 5 行，超過就內部捲動
  const CHAT_FIELD_MAX_HEIGHT = 118

  const draft = ref('')
  const scrollRef = ref<HTMLElement | null>(null)
  const fieldRef = ref<HTMLTextAreaElement | null>(null)

  function autoGrow (): void {
    const el = fieldRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, CHAT_FIELD_MAX_HEIGHT)}px`
    // 未達上限就不留 scrollbar
    el.style.overflowY = el.scrollHeight > CHAT_FIELD_MAX_HEIGHT ? 'auto' : 'hidden'
  }

  function onFieldKeydown (event: KeyboardEvent): void {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
    event.preventDefault()
    submit()
  }

  function submit (): void {
    const message = draft.value.trim()
    if (!message || props.pending) return
    draft.value = ''
    if (fieldRef.value) {
      fieldRef.value.style.height = 'auto'
      fieldRef.value.style.overflowY = 'hidden'
    }
    emit('send', message)
  }

  // 還原舊對話也會讓 length 由 0 變 N，所以重整後直接停在最新一則
  watch(
    [() => props.history.length, () => props.pending],
    async () => {
      await nextTick()
      if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    },
  )
</script>

<style scoped>
  /* 底色、邊框、圓角、陰影由 .glass-panel 提供。scoped 樣式不在 CSS layer 內、
     優先權高於 glass.css，在這裡重寫任何一項都會蓋掉玻璃 */
  .mapping-chat {
    display: flex;
    flex-direction: column;
    /* 跟著視窗高度走，小螢幕不會被擠到要捲，大螢幕不會留一大片空白 */
    height: clamp(420px, calc(100vh - 190px), 720px);
    overflow: hidden;
  }

  /* 比照 ResultView 的 .analysis-icon-wrap，讓兩邊的 AI 區塊維持一致 */
  .chat-head-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);
    background: color-mix(in oklab, var(--color-ink) 8%, white);
    color: var(--color-ink);
  }

  .chat-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--color-border);
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .chat-offline {
    padding: 10px 16px;
    background: var(--color-warning-bg);
    border-bottom: 1px solid var(--color-warning-bg);
    font-size: 12px;
    color: var(--color-warning-text);
  }

  .chat-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .chat-bubble {
    max-width: 88%;
    padding: 10px 14px;
    border-radius: var(--radius-md);
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .chat-bubble--user {
    align-self: flex-end;
    background: var(--color-chat-user);
    color: var(--color-inverted);
  }

  /* 白底 + 投影，靠高度浮在玻璃面板上 */
  .chat-bubble--assistant {
    align-self: flex-start;
    background: var(--color-chat-system);
    box-shadow:
      0 1px 2px rgba(14, 30, 66, 0.1),
      0 6px 16px rgba(14, 30, 66, 0.07);
    color: var(--color-text);
  }

  .chat-bubble--pending,
  .chat-bubble--opener {
    color: var(--color-ink-soft);
  }

  .chat-input {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid var(--color-border);
  }

  .chat-field {
    flex: 1;
    min-width: 0;
    max-height: 118px;
    padding: 8px 10px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    font-size: 13px;
    font-family: inherit;
    line-height: 1.5;
    resize: none;
    overflow-y: hidden;
  }

  .chat-field:disabled {
    background: var(--color-surface-alt);
  }

  .chat-send {
    flex-shrink: 0;
    height: 36px;
  }
</style>
