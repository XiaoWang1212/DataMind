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
          <label class="form-label" for="login-password">密碼</label>
          <input
            id="login-password"
            v-model="password"
            class="form-input"
            placeholder="輸入密碼"
            required
            type="password"
          >
        </div>
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '登入中...' : '登入' }}
        </button>
      </form>

      <button class="auth-dev-btn" type="button" @click="fillAdminCredentials">
        使用管理員帳號（開發用）
      </button>

      <p class="auth-switch">
        還沒有帳號？<RouterLink to="/register">註冊</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { useAuthStore } from '@/store/authStore'

  const DEV_ADMIN_EMAIL = 'admin@datamind.local'
  const DEV_ADMIN_PASSWORD = 'changeme-locally'

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

.auth-dev-btn {
  width: 100%;
  height: 36px;
  margin-top: 12px;
  background: #ffffff;
  color: var(--color-secondary);
  border: 1px dashed #d1d5db;
  border-radius: 7px;
  font-size: 12.5px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.auth-dev-btn:hover {
  color: var(--color-text);
  border-color: var(--color-accent);
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
