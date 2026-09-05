<template>
  <span class="app-checkbox" :class="{ 'app-checkbox--disabled': disabled }">
    <input
      :aria-label="ariaLabel"
      :checked="modelValue"
      class="app-checkbox-input"
      :disabled="disabled"
      type="checkbox"
      @change="onChange"
    >
    <span aria-hidden="true" class="app-checkbox-box">
      <svg class="app-checkbox-tick" viewBox="0 0 16 16">
        <path
          d="M3.5 8.5 L6.5 11.5 L12.5 4.5"
          fill="none"
          stroke="currentColor"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2.2"
        />
      </svg>
    </span>
  </span>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{
    modelValue: boolean
    disabled?: boolean
    ariaLabel?: string
  }>(), {
    disabled: false,
    ariaLabel: undefined,
  })

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
  }>()

  function onChange (event: Event): void {
    emit('update:modelValue', (event.target as HTMLInputElement).checked)
  }
</script>

<style scoped>
  .app-checkbox {
    position: relative;
    display: inline-flex;
    flex: none;
    width: 18px;
    height: 18px;
  }

  /* 原生 input 疊在方框上並保持可聚焦，鍵盤操作與表單語意才不會斷掉 */
  .app-checkbox-input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    opacity: 0;
    cursor: pointer;
  }

  .app-checkbox-input:disabled {
    cursor: not-allowed;
  }

  .app-checkbox-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    border: 1.5px solid var(--color-border-strong);
    border-radius: 5px;
    background: var(--color-surface);
    transition: background-color 140ms ease, border-color 140ms ease;
  }

  .app-checkbox-tick {
    width: 14px;
    height: 14px;
    color: var(--color-inverted);
    opacity: 0;
    transform: scale(0.7);
    transition: opacity 140ms ease, transform 140ms ease;
  }

  .app-checkbox-input:hover:not(:disabled) + .app-checkbox-box {
    border-color: var(--color-ink);
  }

  .app-checkbox-input:checked + .app-checkbox-box {
    /* 打勾是淺色的，底得用兩個主題都深的 ink-solid；ink 在深色主題是淺藍 */
    border-color: var(--color-ink-solid);
    background: var(--color-ink-solid);
  }

  .app-checkbox-input:checked + .app-checkbox-box .app-checkbox-tick {
    opacity: 1;
    transform: scale(1);
  }

  .app-checkbox-input:focus-visible + .app-checkbox-box {
    outline: 2px solid var(--color-ink-vivid);
    outline-offset: 2px;
  }

  .app-checkbox--disabled .app-checkbox-box {
    opacity: 0.45;
  }
</style>
