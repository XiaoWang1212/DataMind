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
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '註冊中...' : '註冊' }}
        </button>
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

.auth-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
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

.auth-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0;
  font-size: 12px;
  color: var(--color-secondary);
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e8e8e8;
}

.google-btn {
  display: flex;
  justify-content: center;
}
</style>
