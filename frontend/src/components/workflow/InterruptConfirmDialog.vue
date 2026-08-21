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
        <button
          class="interrupt-confirm-btn interrupt-confirm-btn--secondary"
          type="button"
          @click="emit('cancel')"
        >
          取消
        </button>
        <button
          class="interrupt-confirm-btn interrupt-confirm-btn--primary"
          type="button"
          @click="emit('confirm')"
        >
          確定中斷
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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
    border-radius: 14px;
    padding: 24px;
    max-width: 380px;
    width: 90%;
    box-shadow: 0 20px 48px rgba(15, 23, 42, 0.24);
  }

  .interrupt-confirm-card h3 {
    margin: 0 0 8px;
    font-size: 17px;
    color: var(--color-ink);
  }

  .interrupt-confirm-card p {
    margin: 0 0 20px;
    font-size: 13px;
    color: var(--color-secondary);
    line-height: 1.5;
  }

  .interrupt-confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .interrupt-confirm-btn {
    padding: 9px 16px;
    border-radius: 8px;
    border: none;
    font-size: 13px;
    cursor: pointer;
  }

  .interrupt-confirm-btn--secondary {
    background: var(--color-primary);
    color: var(--color-ink);
    border: 1px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
  }

  .interrupt-confirm-btn--primary {
    background: var(--color-accent);
    color: #fff;
  }
</style>
