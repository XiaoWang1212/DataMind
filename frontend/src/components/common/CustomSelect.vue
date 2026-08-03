<template>
  <div
    ref="triggerRef"
    class="custom-select"
    :class="{ 'is-disabled': disabled, 'is-highlight': highlight, 'is-open': open }"
  >
    <button
      :aria-activedescendant="open && activeIndex >= 0 ? `${uid}-opt-${activeIndex}` : undefined"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :aria-label="ariaLabel"
      class="cs-trigger"
      :disabled="disabled"
      role="combobox"
      type="button"
      @click="toggle"
      @keydown="onTriggerKeydown"
    >
      <span class="cs-label" :class="{ 'is-placeholder': !selectedLabel }">
        {{ selectedLabel ?? placeholder ?? '' }}
      </span>
      <span class="cs-chevron" aria-hidden="true">
        <svg width="16" height="16" viewBox="0 0 24 24"><path fill="currentColor" d="M7 10l5 5 5-5z" /></svg>
      </span>
    </button>

    <Teleport to="body">
      <Transition :css="false" @enter="onPopupEnter" @leave="onPopupLeave">
      <ul
        v-if="open"
        ref="popupRef"
        class="cs-popup"
        role="listbox"
        :style="popupStyle"
        @keydown="onPopupKeydown"
      >
        <li
          v-for="(opt, i) in options"
          :id="`${uid}-opt-${i}`"
          :key="opt.value"
          class="cs-option"
          :class="{
            'is-active': i === activeIndex,
            'is-selected': opt.value === modelValue,
            'is-disabled': opt.disabled,
          }"
          role="option"
          :aria-selected="opt.value === modelValue"
          :aria-disabled="opt.disabled || undefined"
          @mouseenter="activeIndex = i"
          @click="selectOption(opt)"
        >
          {{ opt.label }}
        </li>
      </ul>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

  interface Option { value: string, label: string, disabled?: boolean }

  const props = defineProps<{
    modelValue: string
    options: Option[]
    placeholder?: string
    disabled?: boolean
    highlight?: boolean
    /** 沒有可見標籤時給讀螢幕軟體用，否則它只會唸出目前選到的值 */
    ariaLabel?: string
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: string]
    'change': [value: string]
  }>()

  let uidSeq = 0
  const uid = `cs-${(uidSeq += 1)}-${Math.random().toString(36).slice(2, 8)}`

  const triggerRef = ref<HTMLElement | null>(null)
  const popupRef = ref<HTMLElement | null>(null)
  const open = ref(false)
  const activeIndex = ref(-1)
  const popupStyle = ref<Record<string, string>>({})

  const selectedLabel = computed(
    () => props.options.find(o => o.value === props.modelValue)?.label ?? null,
  )

  function firstEnabledIndex (): number {
    return props.options.findIndex(o => !o.disabled)
  }

  function updatePosition (): void {
    const el = triggerRef.value
    if (!el) return
    const r = el.getBoundingClientRect()
    if (r.bottom < 0 || r.top > window.innerHeight) {
      close()
      return
    }
    popupStyle.value = {
      position: 'fixed',
      top: `${r.bottom + 4}px`,
      left: `${r.left}px`,
      width: `${r.width}px`,
    }
  }

  function openPopup (): void {
    if (props.disabled || open.value) return
    open.value = true
    const sel = props.options.findIndex(o => o.value === props.modelValue)
    activeIndex.value = sel >= 0 ? sel : firstEnabledIndex()
    nextTick(updatePosition)
  }

  function close (): void {
    open.value = false
  }

  function toggle (): void {
    if (open.value) close()
    else openPopup()
  }

  function focusTrigger (): void {
    triggerRef.value?.querySelector('button')?.focus()
  }

  function selectOption (opt: Option): void {
    if (opt.disabled) return
    emit('update:modelValue', opt.value)
    emit('change', opt.value)
    close()
    focusTrigger()
  }

  function moveActive (delta: number): void {
    const n = props.options.length
    if (n === 0) return
    let i = activeIndex.value
    for (let step = 0; step < n; step += 1) {
      i = (i + delta + n) % n
      if (!props.options[i]?.disabled) {
        activeIndex.value = i
        break
      }
    }
  }

  let typeBuffer = ''
  let typeTimer: number | undefined

  function onTypeAhead (ch: string): void {
    typeBuffer += ch.toLowerCase()
    window.clearTimeout(typeTimer)
    typeTimer = window.setTimeout(() => {
      typeBuffer = ''
    }, 500)
    const idx = props.options.findIndex(
      o => !o.disabled && o.label.toLowerCase().startsWith(typeBuffer),
    )
    if (idx >= 0) activeIndex.value = idx
  }

  function onPopupKeydown (e: KeyboardEvent): void {
    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault()
        moveActive(1)
        break
      }
      case 'ArrowUp': {
        e.preventDefault()
        moveActive(-1)
        break
      }
      case 'Enter': {
        e.preventDefault()
        const opt = props.options[activeIndex.value]
        if (opt) selectOption(opt)
        break
      }
      case 'Escape': {
        e.preventDefault()
        close()
        break
      }
      case 'Tab': {
        close()
        break
      }
      default: {
        if (e.key.length === 1) onTypeAhead(e.key)
      }
    }
  }

  function onTriggerKeydown (e: KeyboardEvent): void {
    if (props.disabled) return
    if (!open.value) {
      if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
        e.preventDefault()
        openPopup()
      }
      return
    }
    onPopupKeydown(e)
  }

  function onDocPointer (e: PointerEvent): void {
    const t = e.target as Node
    if (triggerRef.value?.contains(t) || popupRef.value?.contains(t)) return
    close()
  }

  // 展開/收合
  const SLIDE_OPEN_MS = 90
  const SLIDE_CLOSE_MS = 90

  function prefersReduced (): boolean {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function onPopupEnter (el: Element, done: () => void): void {
    const ul = el as HTMLElement
    if (prefersReduced()) {
      done()
      return
    }
    ul.getAnimations().forEach(a => a.cancel())
    const target = Math.min(ul.scrollHeight, 240)
    ul.style.overflow = 'hidden'
    const anim = ul.animate(
      [{ height: '0px', opacity: 0 }, { height: `${target}px`, opacity: 1 }],
      { duration: SLIDE_OPEN_MS, easing: 'ease-out' },
    )
    anim.onfinish = () => {
      ul.style.overflow = ''
      done()
    }
  }

  function onPopupLeave (el: Element, done: () => void): void {
    const ul = el as HTMLElement
    if (prefersReduced()) {
      done()
      return
    }
    ul.getAnimations().forEach(a => a.cancel())
    const start = Math.min(ul.scrollHeight, 240)
    ul.style.overflow = 'hidden'
    const anim = ul.animate(
      [{ height: `${start}px`, opacity: 1 }, { height: '0px', opacity: 0 }],
      { duration: SLIDE_CLOSE_MS, easing: 'ease-in' },
    )
    anim.onfinish = () => {
      ul.style.overflow = ''
      done()
    }
  }

  watch(() => props.disabled, isDisabled => {
    if (isDisabled) close()
  })

  watch(open, isOpen => {
    if (isOpen) {
      document.addEventListener('pointerdown', onDocPointer, true)
      window.addEventListener('scroll', updatePosition, true)
      window.addEventListener('resize', updatePosition)
    } else {
      document.removeEventListener('pointerdown', onDocPointer, true)
      window.removeEventListener('scroll', updatePosition, true)
      window.removeEventListener('resize', updatePosition)
      activeIndex.value = -1
    }
  })

  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onDocPointer, true)
    window.removeEventListener('scroll', updatePosition, true)
    window.removeEventListener('resize', updatePosition)
    window.clearTimeout(typeTimer)
  })
</script>

<style scoped>
  .custom-select {
    position: relative;
    width: 100%;
  }

  .cs-trigger {
    width: 100%;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 0 8px;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    background: #fff;
    color: var(--color-ink);
    font-size: 13px;
    cursor: pointer;
    text-align: left;
  }

  .cs-trigger:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .is-highlight .cs-trigger {
    border-color: #94a3b8;
  }

  /* 展開跟聚焦排在 highlight 後面，才蓋得掉未對應的灰框 */
  .cs-trigger:focus-visible,
  .is-open .cs-trigger {
    border-color: var(--color-accent);
    outline: none;
  }

  .cs-trigger:focus-visible {
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-accent) 20%, transparent);
  }

  .cs-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cs-label.is-placeholder {
    color: #94a3b8;
  }

  .cs-chevron {
    display: flex;
    color: #94a3b8;
    flex-shrink: 0;
    transition: transform 0.15s, color 0.15s;
  }

  .is-open .cs-chevron {
    transform: rotate(180deg);
    color: var(--color-accent);
  }

  .cs-popup {
    margin: 0;
    padding: 4px;
    list-style: none;
    max-height: 240px;
    overflow-y: auto;
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
    z-index: 3000;
  }

  .cs-option {
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 13px;
    color: var(--color-ink);
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cs-option.is-active {
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
  }

  /* accent 本人在白底只有 2.2:1，當文字讀不清楚，改用同色系的深琥珀 */
  .cs-option.is-selected {
    color: #b45309;
    font-weight: 600;
  }

  .cs-option.is-disabled {
    color: #cbd5e1;
    cursor: not-allowed;
  }
</style>
