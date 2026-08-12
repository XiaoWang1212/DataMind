<template>
  <div ref="buttonContainer" class="google-signin-button" />
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'

  declare global {
    interface Window {
      google: {
        accounts: {
          id: {
            initialize: (config: {
              client_id: string
              callback: (response: { credential: string }) => void
            }) => void
            renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void
          }
        }
      }
    }
  }

  const emit = defineEmits<{ credential: [idToken: string] }>()

  const buttonContainer = ref<HTMLElement | null>(null)

  const GIS_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

  function loadGisScript (): Promise<void> {
    if (document.querySelector(`script[src="${GIS_SCRIPT_SRC}"]`)) {
      return Promise.resolve()
    }
    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = GIS_SCRIPT_SRC
      script.async = true
      script.defer = true
      script.addEventListener('load', () => resolve())
      script.addEventListener('error', () => reject(new Error('無法載入 Google 登入元件')))
      document.head.append(script)
    })
  }

  onMounted(async () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined
    if (!clientId || !buttonContainer.value) return

    try {
      await loadGisScript()
    } catch {
      return
    }

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: response => emit('credential', response.credential),
    })
    window.google.accounts.id.renderButton(buttonContainer.value, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      // 配色與字體照 Google 品牌規範走，只把外框改成膠囊，跟旁邊的送出鈕一致
      shape: 'pill',
      width: 320,
    })
  })
</script>
