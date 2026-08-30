<template>
  <div
    v-if="visible"
    class="confirm-dialog-backdrop"
    @click.self="emit('cancel')"
  >
    <div class="confirm-dialog-card">
      <h3>{{ title }}</h3>
      <p>{{ message }}</p>
      <div class="confirm-dialog-actions">
        <AppButton variant="secondary" @click="emit('cancel')">
          {{ cancelText }}
        </AppButton>
        <AppButton variant="danger" @click="emit('confirm')">
          {{ confirmText }}
        </AppButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import AppButton from '@/components/ui/AppButton.vue'

  withDefaults(defineProps<{
    visible: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
  }>(), {
    confirmText: '確定',
    cancelText: '取消',
  })

  const emit = defineEmits<{
    confirm: []
    cancel: []
  }>()
</script>

<style scoped>
  .confirm-dialog-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .confirm-dialog-card {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    padding: 24px;
    max-width: 380px;
    width: 90%;
    box-shadow: var(--shadow-float);
  }

  .confirm-dialog-card h3 {
    margin: 0 0 8px;
    font-size: 17px;
    color: var(--color-ink);
  }

  .confirm-dialog-card p {
    margin: 0 0 20px;
    font-size: 13px;
    color: var(--color-ink-soft);
    line-height: 1.5;
  }

  .confirm-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
</style>
