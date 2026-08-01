/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Composables
import { createApp } from 'vue'

// Plugins
import { registerPlugins } from '@/plugins'

// Store
import { useAuthStore } from '@/store/authStore'
import { useFrameworkStore } from '@/store/frameworkStore'
import { useProjectStore } from '@/store/projectStore'

// Components
import App from './App.vue'

// Styles
import 'unfonts.css'
import './styles/tailwind.css'
import './styles/main.scss'

const app = createApp(App)

registerPlugins(app)

const authStore = useAuthStore()
const projectStore = useProjectStore()
const frameworkStore = useFrameworkStore()

authStore.checkSession().finally(() => {
  app.mount('#app')
})
projectStore.loadProjects()
frameworkStore.loadFrameworks()
