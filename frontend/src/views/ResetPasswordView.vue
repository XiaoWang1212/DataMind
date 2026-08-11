<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">重設密碼</h1>

      <template v-if="!token">
        <p class="auth-sub">這個連結不完整或已失效。</p>
        <p class="auth-switch">
          <RouterLink to="/forgot-password">重新申請重設密碼</RouterLink>
        </p>
      </template>

      <template v-else-if="success">
        <div class="auth-info">密碼已重設完成，請用新密碼登入。</div>
        <p class="auth-switch">
          <RouterLink to="/login">前往登入</RouterLink>
        </p>
      </template>

      <template v-else>
        <p class="auth-sub">設定一組新密碼</p>
        <div v-if="errorMessage" class="auth-error">{{ errorMessage }}</div>
        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="form-field">
            <label class="form-label" for="reset-password">新密碼</label>
            <input
              id="reset-password"
              v-model="password"
              class="form-input"
              placeholder="設定新密碼"
              required
              type="password"
            >
          </div>
          <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
            {{ isSubmitting ? '重設中...' : '重設密碼' }}
          </button>
        </form>
        <p class="auth-switch">
          連結失效？<RouterLink to="/forgot-password">重新申請</RouterLink>
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import { resetPassword } from '@/api/auth'

  const route = useRoute()
  const token = (route.query.token as string | undefined) ?? ''

  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)
  const success = ref(false)

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await resetPassword(token, password.value)
      success.value = true
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 32px;
  color: var(--color-text);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 5px;
}

.auth-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0 0 20px;
}

.auth-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.auth-info {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #15803d;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-text);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-input::placeholder {
  color: var(--color-secondary);
}

.form-input:focus {
  border-color: var(--color-accent);
}

.auth-submit-btn {
  width: 100%;
  height: 40px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.auth-submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.auth-switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-secondary);
  margin: 18px 0 0;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
