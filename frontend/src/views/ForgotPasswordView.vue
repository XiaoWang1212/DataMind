<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">忘記密碼</h1>
      <p class="auth-sub">輸入註冊時使用的 email，我們會寄送重設密碼連結</p>

      <div v-if="submitted" class="auth-info">
        若此 email 已註冊，重設密碼信已寄出，請檢查你的信箱。
      </div>

      <form v-else class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="form-label" for="forgot-email">Email</label>
          <input
            id="forgot-email"
            v-model="email"
            class="form-input"
            placeholder="you@example.com"
            required
            type="email"
          >
        </div>
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '送出中...' : '送出重設連結' }}
        </button>
      </form>

      <p class="auth-switch">
        想起密碼了？<RouterLink to="/login">回到登入</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink } from 'vue-router'
  import { forgotPassword } from '@/api/auth'

  const email = ref('')
  const isSubmitting = ref(false)
  const submitted = ref(false)

  async function handleSubmit (): Promise<void> {
    isSubmitting.value = true
    try {
      await forgotPassword(email.value)
    } catch {
      // 不論成功或失敗都顯示同一句訊息，避免洩漏 email 是否已註冊
    } finally {
      isSubmitting.value = false
      submitted.value = true
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
  color: var(--color-ink);
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
  color: var(--color-ink);
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
