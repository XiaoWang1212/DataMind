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
        <AppButton class="auth-submit-btn" :loading="isSubmitting" type="submit" variant="primary">
          送出重設連結
        </AppButton>
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
  import AppButton from '@/components/ui/AppButton.vue'

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
