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
          'primary': '#1A3159',
          // ink-soft：次要文字、說明、icon
          'secondary': '#626B7E',
          // accent 名稱保留給尚未遷移的既有頁面用（167 處引用），數值已從金色改成品牌藏青，
          // 之後個別頁面遷移時應改直接引用 primary，屆時再考慮拿掉這個 key
          'accent': '#1A3159',
          // page：頁面底色。實際畫面會被 main.scss 的漸層蓋掉，這裡是漸層底下的純色 fallback
          'background': '#E4E9ED',
          'surface': '#FFFFFF',
          // 色相往冷調偏（綠→青綠、紅→玫瑰紅）跟藏青同色溫，飽和度維持在 0.45 以上，
          // 三色都貼著圖形元素 3:1 的下限，再提亮或再降飽和就會不合格
          'success': '#3B9A7F',
          'warning': '#C88819',
          // docs/DESIGN_SYSTEM.md 稱這個角色為 danger，這裡沿用 Vuetify 內建的 error 插槽名稱
          'error': '#D7445C',
          // 品牌藏青深一階：hover/按下、標題強調
          // 「不隨主題翻面」的實色深底，專門承載 --color-inverted 淺字（見 DESIGN_SYSTEM §2.5）。
          // 不能用 ink：它在深色主題翻成淺藍，淺字疊上去會看不見
          'ink-solid': '#1A3159',
          // 同一組深底的暗端，只給漸層當第二個色停
          'ink-solid-deep': '#1B2C4C',
          // AI 按鈕的漸層兩端，同樣兩個主題都必須是深的
          'ai-from': '#2B5CA8',
          'ai-to': '#12244A',
          'ink-strong': '#12244A',
          // 藏青亮一階。ink 疊在深色內文旁邊看不出差別時用，例如選單的已選項目
          'ink-vivid': '#2B5CA8',
          // 內文深色文字。原本借用 primary 的位置（--color-ink），Task 1 已把舊引用改名讓出這裡
          'text': '#1C2130',
          // 次級底：表頭、hover 背景、工具列。偏冷的淺灰藍，跟頁面漸層與藏青同一個色溫
          // （舊值 #F6F5F2 是暖米白，金色主題的遺留，疊在冷色背景上會顯髒）
          'surface-alt': '#F1F4F8',
          // 一般分隔線
          'border': '#E4E6E8',
          // 強調分隔、輸入框邊界
          'border-strong': '#D3D8DC',
          'success-bg': '#DCEAE5',
          'warning-bg': '#F7EECF',
          'error-bg': '#F2DEE2',
          // 徽章文字疊在對應的 -bg 淺底上時，圓點色的對比不足 4.5:1，文字另用深一階的值
          // 量到的對比：5.88 / 4.77 / 5.40:1，皆過 §2.4 的 WCAG AA 4.5:1
          'success-text': '#1D6151',
          'warning-text': '#835A07',
          'error-text': '#A22F43',
          // 期刊評分低分的進度條填色。對比不足 4.5:1，不可當文字色
          'score-low': '#E6B800',
          // workflow 節點分類色（docs/DESIGN_SYSTEM.md §2.3）。依 pipeline 角色分五類，
          // 依 Orange Data Mining 的六類配色大致順序（橘/藍/紫/綠/紅）指派，OKLCH 明度/彩度
          // 統一（L=0.76 C=0.058，只有色相不同）。跟 success/warning/error 三個狀態色的
          // 色相距離沒有嚴格要求——這組色相跟狀態色偶有貼近（例如 source 對 error 只差 24°），
          // 是刻意換取「一眼看得出是 Orange 配色語彙」的結果，靠淺底+邊框+深色 icon 的構造
          // 而非色相距離本身來避免混淆
          'node-source': '#D2A596',
          'node-transform': '#8EB8D1',
          'node-visualize': '#A9AED6',
          'node-model': '#85BDBC',
          'node-evaluate': '#CFA3B6',
          // 原本寫死在 tailwind.css，改成主題插槽讓深色有對應值。
          // AI 氣泡用純白＋投影浮在玻璃面板上，靠高度而不是明度差區分；
          // 使用者氣泡用品牌藏青實色
          'chat-system': '#FFFFFF',
          'chat-user': '#1A3159',
        },
      },
      // 深色底走中性石墨、不帶色相：狀態色與節點分類色跳得更開，資料比較好讀。
      // 代價是少了藏青的品牌識別，這是刻意的取捨（見 spec §色票）
      dark: {
        dark: true,
        colors: {
          // ink 系列從深藏青翻成淺藍：深底上要維持 4.5:1 就不可能沿用原本的深色值。
          // 色相留在藏青範圍（220° 附近），兩個模式仍是同一個品牌
          'primary': '#8FB4EE',
          'secondary': '#9BA1A8',
          'accent': '#8FB4EE',
          'background': '#141618',
          'surface': '#1F2225',
          'success': '#4FC79E',
          'warning': '#E0A93F',
          'error': '#F0687F',
          // 深色的實色底比淺色亮一階但仍是深色：#2F5288 對 #F1F5F9 是 7.14:1
          'ink-solid': '#2F5288',
          'ink-solid-deep': '#1F3A63',
          'ai-from': '#2C4A86',
          'ai-to': '#1C3358',
          'ink-strong': '#B4CDF5',
          'ink-vivid': '#5B8FD8',
          'text': '#E8EAEC',
          'surface-alt': '#26292D',
          'border': '#33373C',
          'border-strong': '#454A50',
          'success-bg': '#16342B',
          'warning-bg': '#3A2E12',
          'error-bg': '#3A1D25',
          'success-text': '#6ADCB6',
          'warning-text': '#F0C46A',
          'error-text': '#FF8FA2',
          'score-low': '#E8C24A',
          // 節點分類色維持與淺色相同：這五個是中明度粉彩，直接當填色鋪在石墨底上
          // 依然清楚，上面疊的深色文字也不受背景影響。翻成「深底＋亮色 icon」
          // 要改 IconNode 的結構，而且畫布會失去 Orange Data Mining 的配色識別
          'node-source': '#D2A596',
          'node-transform': '#8EB8D1',
          'node-visualize': '#A9AED6',
          'node-model': '#85BDBC',
          'node-evaluate': '#CFA3B6',
          // AI 氣泡用次級底、使用者氣泡用亮一階的藏青，維持「一邊靠層次、一邊靠實色」
          'chat-system': '#26292D',
          'chat-user': '#2B5CA8',
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
