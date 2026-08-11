/**
 * plugins/vuetify.ts
 *
 * Framework documentation: https://vuetifyjs.com
 */

import { createVuetify } from 'vuetify'
import '@mdi/font/css/materialdesignicons.css'
import '../styles/layers.css'
import 'vuetify/styles'

export default createVuetify({
  theme: {
    defaultTheme: 'light',
    utilities: false,
    themes: {
      light: {
        colors: {
          // 品牌藏青（docs/DESIGN_SYSTEM.md §2.2 ink）：主要按鈕、選中、重點
          primary: '#1A3159',
          // ink-soft：次要文字、說明、icon
          secondary: '#626B7E',
          // accent 名稱保留給尚未遷移的既有頁面用（167 處引用），數值已從金色改成品牌藏青，
          // 之後個別頁面遷移時應改直接引用 primary，屆時再考慮拿掉這個 key
          accent: '#1A3159',
          // page：頁面底色。實際畫面會被 main.scss 的漸層蓋掉，這裡是漸層底下的純色 fallback
          background: '#E4E9ED',
          surface: '#FFFFFF',
          success: '#1F7A44',
          warning: '#C9822E',
          // docs/DESIGN_SYSTEM.md 稱這個角色為 danger，這裡沿用 Vuetify 內建的 error 插槽名稱
          error: '#C7392E',
          // 品牌藏青深一階：hover/按下、標題強調
          'ink-strong': '#12244A',
          // 內文深色文字。原本借用 primary 的位置（--color-ink），Task 1 已把舊引用改名讓出這裡
          text: '#1C2130',
          // 次級底：表頭、hover 背景、工具列
          'surface-alt': '#F6F5F2',
          // 一般分隔線
          border: '#E4E6E8',
          // 強調分隔、輸入框邊界
          'border-strong': '#D3D8DC',
          'success-bg': '#DCEDE3',
          'warning-bg': '#F5E9D8',
          'error-bg': '#F5DEDC',
          // 徽章文字疊在對應的 -bg 淺底上時，圓點色的對比不足 4.5:1，文字另用深一階的值
          'success-text': '#176B39',
          'warning-text': '#8F560A',
          'error-text': '#B8342A',
          // workflow 節點分類色（docs/DESIGN_SYSTEM.md §2.3）。人工確認/完成複用 warning/success，不重複定義
          'node-data': '#5B7A9D',
          'node-ai': '#6B5B95',
        },
      },
    },
  },
  display: {
    mobileBreakpoint: 'md',
    thresholds: {
      xs: 0,
      sm: 600,
      md: 840,
      lg: 1145,
      xl: 1545,
      xxl: 2138,
    },
  },
})
