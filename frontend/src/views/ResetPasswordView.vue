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
          <AppButton class="auth-submit-btn" :loading="isSubmitting" type="submit" variant="primary">
            重設密碼
          </AppButton>
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
  import AppButton from '@/components/ui/AppButton.vue'

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
/* 頁面漸層畫在 .v-application 上，這裡不鋪底色才透得出來 */
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: 32px;
  color: var(--color-text);
}

.auth-title {
  font-size: 22px;
  font-weight: 500;
  margin: 0 0 5px;
}

.auth-sub {
  font-size: 13px;
  color: var(--color-ink-soft);
  margin: 0 0 20px;
}

.auth-error {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border-radius: var(--radius-sm);
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.auth-info {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border-radius: var(--radius-sm);
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ink-soft);
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--color-text);
  background-color: var(--color-surface);
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--dur-fast) var(--ease-out);
  color-scheme: light;
}

.form-input::placeholder {
  color: var(--color-ink-soft);
}

.form-input:focus {
  border-color: var(--color-ink);
}

.auth-submit-btn {
  width: 100%;
  height: 40px;
  margin-top: 4px;
}

.auth-switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-ink-soft);
  margin: 18px 0 0;
}

.auth-switch a {
  color: var(--color-ink);
  font-weight: 500;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
