<template>
  <div
    v-if="visible"
    class="interrupt-confirm-backdrop"
    @click.self="emit('cancel')"
  >
    <div class="interrupt-confirm-card">
      <h3>確定要中斷嗎？</h3>
      <p>{{ message }}</p>
      <div class="interrupt-confirm-actions">
        <AppButton variant="secondary" @click="emit('cancel')">
          取消
        </AppButton>
        <AppButton variant="danger" @click="emit('confirm')">
          確定中斷
        </AppButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import AppButton from '@/components/ui/AppButton.vue'

  defineProps<{
    visible: boolean
    message: string
  }>()

  const emit = defineEmits<{
    confirm: []
    cancel: []
  }>()
</script>

<style scoped>
  .interrupt-confirm-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .interrupt-confirm-card {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    padding: 24px;
    max-width: 380px;
    width: 90%;
    box-shadow: var(--shadow-float);
  }

  .interrupt-confirm-card h3 {
    margin: 0 0 8px;
    font-size: 17px;
    color: var(--color-ink);
  }

  .interrupt-confirm-card p {
    margin: 0 0 20px;
    font-size: 13px;
    color: var(--color-ink-soft);
    line-height: 1.5;
  }

  .interrupt-confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
</style>
