<template>
  <div ref="trackRef" class="mode-switch">
    <span ref="pillRef" class="pill" />
    <button
      ref="viewBtnRef"
      class="mode-switch-btn"
      :class="{ active: modelValue === 'view' }"
      :disabled="disabled || (locked && modelValue !== 'view')"
      type="button"
      @click="select('view')"
    >
      檢視
    </button>
    <button
      ref="editBtnRef"
      class="mode-switch-btn"
      :class="{ active: modelValue === 'edit' }"
      :disabled="disabled"
      type="button"
      @click="select('edit')"
    >
      編輯
    </button>
  </div>
</template>

<script setup lang="ts">
  import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

  const props = withDefaults(defineProps<{
    modelValue: 'view' | 'edit'
    disabled?: boolean
    locked?: boolean
  }>(), {
    disabled: false,
    locked: false,
  })

  const emit = defineEmits<{
    (e: 'update:modelValue', mode: 'view' | 'edit'): void
  }>()

  const trackRef = ref<HTMLElement | null>(null)
  const pillRef = ref<HTMLElement | null>(null)
  const viewBtnRef = ref<HTMLButtonElement | null>(null)
  const editBtnRef = ref<HTMLButtonElement | null>(null)

  function targetBtn (mode: 'view' | 'edit'): HTMLButtonElement | null {
    return mode === 'view' ? viewBtnRef.value : editBtnRef.value
  }

  function movePillTo (mode: 'view' | 'edit') {
    const btn = targetBtn(mode)
    const pill = pillRef.value
    if (!btn || !pill) return
    pill.style.left = `${btn.offsetLeft}px`
    pill.style.width = `${btn.offsetWidth}px`
  }

  function select (mode: 'view' | 'edit') {
    if (props.disabled) return
    if (mode === props.modelValue) return
    if (props.locked) return
    emit('update:modelValue', mode)
  }

  function handleResize () {
    movePillTo(props.modelValue)
  }

  watch(() => props.modelValue, mode => {
    movePillTo(mode)
  })

  onMounted(async () => {
    await nextTick()
    movePillTo(props.modelValue)
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
  })
</script>

<style scoped>
  .mode-switch {
    position: relative;
    display: inline-flex;
    align-items: center;
    padding: 3px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.5);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.7);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.5),
      var(--shadow-card);
  }

  .pill {
    position: absolute;
    top: 3px;
    bottom: 3px;
    left: 0;
    width: 0;
    border-radius: 999px;
    background: var(--color-ink);
    transition:
      left var(--dur-slow) var(--ease-in-out),
      width var(--dur-slow) var(--ease-in-out);
  }

  .mode-switch-btn {
    position: relative;
    z-index: 1;
    padding: 5px 16px;
    border: none;
    background: transparent;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink-soft);
    cursor: pointer;
    transition: color var(--dur-slow) var(--ease-in-out);
  }

  .mode-switch-btn:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .mode-switch-btn.active {
    color: var(--color-inverted);
  }
</style>
