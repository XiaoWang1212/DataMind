<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">註冊</h1>
      <p class="auth-sub">建立一個新的 DataMind 帳號</p>

      <div v-if="errorMessage" class="auth-error">{{ errorMessage }}</div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="form-label" for="register-email">Email</label>
          <input
            id="register-email"
            v-model="email"
            class="form-input"
            placeholder="you@example.com"
            required
            type="email"
          >
        </div>
        <div class="form-field">
          <label class="form-label" for="register-display-name">顯示名稱（選填）</label>
          <input
            id="register-display-name"
            v-model="displayName"
            class="form-input"
            placeholder="你的名字"
            type="text"
          >
        </div>
        <div class="form-field">
          <label class="form-label" for="register-password">密碼</label>
          <input
            id="register-password"
            v-model="password"
            class="form-input"
            placeholder="設定密碼"
            required
            type="password"
          >
        </div>
        <AppButton class="auth-submit-btn" :loading="isSubmitting" type="submit" variant="primary">
          註冊
        </AppButton>
      </form>

      <template v-if="hasGoogleClientId">
        <div class="auth-divider"><span>或</span></div>
        <GoogleSignInButton class="google-btn" @credential="handleGoogleCredential" />
      </template>

      <p class="auth-switch">
        已經有帳號？<RouterLink to="/login">登入</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import GoogleSignInButton from '@/components/auth/GoogleSignInButton.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import { useAuthStore } from '@/store/authStore'

  const hasGoogleClientId = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const displayName = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.register(email.value, password.value, displayName.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }

  async function handleGoogleCredential (idToken: string): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.loginWithGoogle(idToken)
      router.push('/hub/dashboard')
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

.auth-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0;
  font-size: 12px;
  color: var(--color-ink-soft);
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.google-btn {
  display: flex;
  justify-content: center;
}
</style>
