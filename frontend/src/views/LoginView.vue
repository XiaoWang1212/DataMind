<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">登入</h1>
      <p class="auth-sub">登入以繼續使用 DataMind</p>

      <div v-if="errorMessage" class="auth-error">{{ errorMessage }}</div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="form-label" for="login-email">Email</label>
          <input
            id="login-email"
            v-model="email"
            class="form-input"
            placeholder="you@example.com"
            required
            type="email"
          >
        </div>
        <div class="form-field">
          <div class="form-label-row">
            <label class="form-label" for="login-password">密碼</label>
            <RouterLink class="forgot-link" to="/forgot-password">忘記密碼？</RouterLink>
          </div>
          <input
            id="login-password"
            v-model="password"
            class="form-input"
            placeholder="輸入密碼"
            required
            type="password"
          >
        </div>
        <AppButton class="auth-submit-btn" :loading="isSubmitting" type="submit" variant="primary">
          登入
        </AppButton>
      </form>

      <template v-if="hasGoogleClientId">
        <div class="auth-divider"><span>或</span></div>
        <GoogleSignInButton class="google-btn" @credential="handleGoogleCredential" />
      </template>

      <AppButton class="auth-dev-btn" variant="ghost" @click="fillAdminCredentials">
        使用管理員帳號（開發用）
      </AppButton>

      <p class="auth-switch">
        還沒有帳號？<RouterLink to="/register">註冊</RouterLink>
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

  const DEV_ADMIN_EMAIL = 'admin@datamind.local'
  const DEV_ADMIN_PASSWORD = 'changeme-locally'

  const hasGoogleClientId = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  function fillAdminCredentials (): void {
    email.value = DEV_ADMIN_EMAIL
    password.value = DEV_ADMIN_PASSWORD
  }

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.login(email.value, password.value)
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

/* 用 .auth-card 加權，蓋掉 AppButton 自己的 border: none */
.auth-card .auth-dev-btn {
  box-sizing: border-box;
  width: 100%;
  height: 36px;
  margin-top: 12px;
  /* 虛線界定範圍，同時暗示這是開發用捷徑而非正式動作 */
  border: 1px dashed var(--color-border-strong);
  font-size: 13px;
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

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.forgot-link {
  font-size: 13px;
  color: var(--color-ink);
  text-decoration: none;
}

.forgot-link:hover {
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
