<template>
  <aside class="mapping-chat">
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
      <div
        v-for="(message, i) in history"
        :key="i"
        class="chat-bubble"
        :class="`chat-bubble--${message.role}`"
      >
        {{ message.content }}
      </div>
      <div v-if="pending" class="chat-bubble chat-bubble--assistant chat-bubble--pending">
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
      <button
        class="chat-send"
        :disabled="!available || pending || !draft.trim()"
        type="submit"
      >
        送出
      </button>
    </form>
  </aside>
</template>

<script setup lang="ts">
  import type { ChatMessage } from '@/types/fieldMapping'
  import { nextTick, ref, watch } from 'vue'

  const props = defineProps<{
    history: ChatMessage[]
    pending: boolean
    available: boolean
    loading: boolean
  }>()

  const emit = defineEmits<{
    send: [message: string]
  }>()

  // 開場白：不進 history，不存草稿
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
    // 沒滿高度就不留 scrollbar，一行字的時候才不會看起來怪怪的
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

  // 訊息數或「思考中」狀態一變就捲到最新一則。
  // 原本由頁面在送出前後各呼叫一次，改由面板監看自己的 props。
  // 附帶一個刻意保留的差異：頁面載入時從 localStorage 還原舊對話也會讓 length 由 0 變 N，
  // 因此重整後會直接停在最新一則（重構前是停在最上面）。這比較符合聊天介面的預期，故保留。
  watch(
    [() => props.history.length, () => props.pending],
    async () => {
      await nextTick()
      if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    },
  )
</script>

<style scoped>
  .mapping-chat {
    display: flex;
    flex-direction: column;
    /* 跟著視窗高度走：筆電上不會被擠到要捲，大螢幕也不會留一大片空白 */
    height: clamp(420px, calc(100vh - 190px), 720px);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    background: #fff;
    overflow: hidden;
  }

  /* 圖示樣式比照 ResultView 的 .analysis-icon-wrap，兩邊的 AI 區塊看起來才是一組的 */
  .chat-head-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: #eef1ff;
    color: var(--color-accent);
  }

  .chat-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid #e8e8e8;
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text);
  }

  .chat-offline {
    padding: 10px 16px;
    background: #fffbeb;
    border-bottom: 1px solid #fde68a;
    font-size: 12px;
    color: #b45309;
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
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .chat-bubble--user {
    align-self: flex-end;
    background: var(--color-chat-user);
    color: var(--color-inverted);
  }

  .chat-bubble--assistant {
    align-self: flex-start;
    background: var(--color-chat-system);
    color: var(--color-text);
  }

  .chat-bubble--pending {
    color: #94a3b8;
  }

  .chat-bubble--opener {
    align-self: flex-start;
    background: var(--color-background);
    color: var(--color-secondary);
  }

  .chat-input {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid #e8e8e8;
  }

  .chat-field {
    flex: 1;
    min-width: 0;
    max-height: 118px;
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    font-size: 13px;
    font-family: inherit;
    line-height: 1.5;
    resize: none;
    overflow-y: hidden;
  }

  .chat-field:disabled {
    background: var(--color-background);
  }

  .chat-send {
    flex-shrink: 0;
    padding: 0 16px;
    height: 36px;
    border: none;
    border-radius: 7px;
    background: var(--color-accent);
    color: #ffffff;
    cursor: pointer;
    transition: background 0.15s;
    font-size: 13px;
    font-weight: 600;
  }

  .chat-send:hover:not(:disabled) {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }

  .chat-send:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
</style>
