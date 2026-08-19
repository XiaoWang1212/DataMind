export default {
  blocklist: [
    // 這份 blocklist 是這次計畫之前就有的，目的是擋掉 Tailwind 內建、未經專案核准的圓角尺度
    // （當時自訂圓角只有 sm/lg/xl 三個）。rounded-md 跟 rounded-full 現在不能再被擋了：
    // docs/DESIGN_SYSTEM.md §4.2 的圓角尺度已經包含 md（見 tailwind.css 的 --radius-md
    // 與 @utility rounded-md），pill 形狀則是刻意選擇沿用 Tailwind 內建的 rounded-full
    // (9999px)、不另外造 token（見 /style-guide 展示頁）。
    'rounded-xs',
    'rounded-2xl',
    'rounded-3xl',
    'rounded-4xl',
  ],
  safelist: [
    '--font-body',
    '--font-heading',
    '--font-mono',
    // Vuetify 的 color prop（如 <v-btn color="success">）在執行期才組出 bg-success 這類
    // class 字串，原始碼裡從未出現過字面文字，Tailwind 的 JIT 掃描器偵測不到、不會產生對應
    // utility。這裡強制安全列出，確保 tailwind.css 裡補上前景色的 bg-* 覆蓋一定會被輸出。
    'bg-primary',
    'bg-secondary',
    'bg-accent',
    'bg-success',
    'bg-warning',
    'bg-error',
  ],
}
