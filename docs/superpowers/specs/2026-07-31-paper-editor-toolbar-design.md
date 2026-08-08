# 論文編輯器工具列增強

## 背景

`PaperEditor.vue` 是論文編輯頁（`PaperPage.vue`）的 Tiptap 富文本編輯器元件，目前工具列只有基本格式（粗體/斜體/底線/刪除線）、標題、清單、引用、對齊、插入表格（固定 3×3）、插入圖表（`InsertChartDialog`）、復原/重做。使用者反應撰寫論文時工具不夠用，希望能插入一般圖片（並能調整置中與大小），也請我自行補上其他撰寫論文時常見的必要功能。

透過視覺化 mockup 比較後，確定工具列的視覺方向從目前的白底細邊框改成跟 `HubSidebar.vue`／`ModeSwitch.vue` 同一套毛玻璃質感的浮動 Dock 樣式（B 版），圖示 hover 會浮現文字提示。

功能範圍經討論後收斂為：超連結、上標/下標、表格列/欄新增刪除、字數統計、一般圖片插入（含對齊與預設尺寸）。Word 風格的自動分頁與 APA/IEEE/MLA 文獻格式管理明確排除在這次範圍外，留給未來獨立的 brainstorming。

## 目標

1. 新增超連結、上標、下標三個文字格式功能
2. 表格內新增/刪除列、新增/刪除欄的操作，游標在表格內時才顯示
3. 編輯器下方常駐顯示即時字數統計
4. 新增獨立的「插入圖片」功能（上傳本機檔案），選取圖片時工具列切換成對齊（左/中/右）+ 預設尺寸（25%/50%/75%/100%）的專屬控制列
5. `.editor-toolbar` 視覺改為毛玻璃浮動 Dock 樣式，按鈕 hover 顯示文字提示

## 非目標

- 不做 Word 風格的自動分頁（留待未來獨立設計）
- 不做文獻管理／APA、IEEE、MLA 引用格式設定（留待未來獨立設計，`CitationMark`／`CitationPopover` 既有的引用機制不變）
- 圖片尺寸不做拖曳把手自由縮放，只提供四段預設百分比
- 不改變既有的插入表格（固定 3×3）、插入圖表（`InsertChartDialog`）按鈕行為
- 不新增自訂 Vuetify 主題元件；沿用專案既有的 `color-mix` token 與已建立的玻璃 CSS 手法

## 設計

### 段落 A：新增套件

```bash
npm install @tiptap/extension-link @tiptap/extension-superscript @tiptap/extension-subscript @tiptap/extension-character-count
```

版本比照現有 tiptap 套件的 `^3.29.x` 系列。

表格列/欄的新增刪除指令（`addRowAfter` / `deleteRow` / `addColumnAfter` / `deleteColumn`）已內建在現有的 `@tiptap/extension-table` 系列套件中，不需額外安裝。

### 段落 B：圖片插入、對齊與尺寸

現有 `Image.configure({ inline: false })` 只能插入不能對齊/縮放的圖片。改用自訂擴充繼承 `Image`，新增 `align` 與 `width` 屬性：

```ts
// frontend/src/components/paper/alignableImage.ts
import { Image } from '@tiptap/extension-image'

export const AlignableImage = Image.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      align: {
        default: 'center',
        parseHTML: element => element.getAttribute('data-align') || 'center',
        renderHTML: attributes => ({
          'data-align': attributes.align,
        }),
      },
      width: {
        default: '100%',
        parseHTML: element => element.style.width || '100%',
        renderHTML: attributes => ({
          style: `width: ${attributes.width}`,
        }),
      },
    }
  },
})
```

`PaperEditor.vue` 的 extensions 陣列把 `Image.configure({ inline: false })` 換成 `AlignableImage.configure({ inline: false })`。

新增「插入圖片」按鈕（獨立於現有的插入圖表按鈕），點擊觸發隱藏的 `<input type="file" accept="image/*">`，用 `FileReader` 讀成 data URL 後呼叫：

```ts
editor.value?.chain().focus().setImage({ src: dataUrl, align: 'center', width: '100%' }).run()
```

選取圖片節點時（`editor?.isActive('image')` 為 `true`，這個呼叫在既有程式碼中已經是每次 transaction 都會重新求值的響應式呼叫，`editor?.isActive('bold')` 已是相同用法），工具列整個切換成圖片專屬控制列：

- 對齊：左/中/右三顆按鈕，呼叫 `editor.chain().focus().updateAttributes('image', { align: 'left' | 'center' | 'right' }).run()`
- 尺寸：25%／50%／75%／100% 四顆按鈕，呼叫 `editor.chain().focus().updateAttributes('image', { width: '25%' }).run()`（依此類推)

`.editor-content` 的 CSS 新增：

```css
:deep(.editor-content img) {
  display: block;
  max-width: 100%;
  height: auto;
}
:deep(.editor-content img[data-align='left']) { margin: 0 auto 0 0; }
:deep(.editor-content img[data-align='center']) { margin: 0 auto; }
:deep(.editor-content img[data-align='right']) { margin: 0 0 0 auto; }
```

### 段落 C：超連結

新增 `Link.configure({ openOnClick: false, autolink: true })` 到 extensions。工具列新增「插入連結」按鈕，用 Vuetify `v-menu`（以按鈕為 activator）彈出一個小面板：一個網址輸入框 + 「套用」/「移除連結」兩顆按鈕。

- 套用：`editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()`
- 移除：`editor.chain().focus().unsetLink().run()`

面板開啟時，若目前選取範圍已經是連結（`editor?.isActive('link')`），輸入框預先帶入既有的 `href`（用 `editor.getAttributes('link').href` 取得）。

### 段落 D：上標 / 下標

新增 `Superscript` 與 `Subscript` extensions。工具列在底線/刪除線旁邊各加一顆按鈕：

```ts
editor.value?.chain().focus().toggleSuperscript().run()
editor.value?.chain().focus().toggleSubscript().run()
```

啟用狀態判斷比照既有格式按鈕：`editor?.isActive('superscript') ? 'tonal' : 'text'`。

### 段落 E：表格列/欄控制

游標在表格內時（`editor?.isActive('table')`），在既有的「插入表格」按鈕後面動態顯示一組四顆按鈕（`v-if="editor?.isActive('table')"` 包住的 `<template>`），不在表格內時整組不渲染：

```ts
editor.value?.chain().focus().addRowAfter().run()
editor.value?.chain().focus().deleteRow().run()
editor.value?.chain().focus().addColumnAfter().run()
editor.value?.chain().focus().deleteColumn().run()
```

### 段落 F：字數統計

新增 `CharacterCount.configure({})` 到 extensions。`.paper-editor` 內、`.editor-content` 下方新增一個常駐的狀態列：

```html
<div v-if="editable" class="editor-status-bar">
  字數：{{ editor?.storage.characterCount.words() ?? 0 }}
</div>
```

跟 `editor?.isActive(...)` 一樣，`editor?.storage.characterCount.words()` 在模板中的呼叫會隨每次 transaction 響應式更新，不需要額外的 state 或 watch。

### 段落 G：工具列毛玻璃 Dock 視覺改版

`.editor-toolbar` 從目前的白底細邊框改為浮動玻璃膠囊，套用跟 `ModeSwitch.vue`／`HubSidebar.vue` 一致的玻璃參數：

```css
/* 現在 */
.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  border: 1px solid #d8dbe3;
  border-radius: 8px;
  background: var(--color-surface);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  margin: 0 4px;
  background: #d8dbe3;
}
```

```css
/* 改為 */
.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.6),
    0 6px 20px rgba(28, 33, 48, 0.12);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  margin: 0 5px;
  background: rgba(28, 33, 48, 0.15);
}
```

每個 `v-btn` 用一個 `.toolbar-btn-wrap` 包住（`position: relative`），用 `data-tooltip` 屬性 + CSS `::after` 做文字提示，不用 Vuetify 的 `v-tooltip`（視覺上跟玻璃 Dock 主題不一致）：

```html
<div class="toolbar-btn-wrap" data-tooltip="粗體">
  <v-btn icon="mdi-format-bold" size="small" ... />
</div>
```

```css
.toolbar-btn-wrap {
  position: relative;
}

.toolbar-btn-wrap::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1c2130;
  color: #fff;
  font-size: 10px;
  padding: 3px 7px;
  border-radius: 5px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
  z-index: 5;
}

.toolbar-btn-wrap:hover::after {
  opacity: 1;
}

.toolbar-btn-wrap :deep(.v-btn:hover) {
  transform: translateY(-2px);
}
```

圖片專屬控制列（段落 B 提到、`editor?.isActive('image')` 為真時顯示的那一條）套用同一份 `.editor-toolbar` 樣式，維持視覺一致。

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 在論文編輯頁切到編輯模式：
  - 工具列呈現毛玻璃浮動 Dock 樣式，圖示 hover 時上浮並顯示文字提示
  - 選取文字後點插入連結，套用網址，確認文字變成可點擊連結樣式；再次點選同一段文字可看到網址預先帶入，移除連結後樣式消失
  - 選取文字套用上標/下標，確認顯示效果正確
  - 游標移進表格，確認出現新增/刪除列/欄四顆按鈕；游標移出表格，確認按鈕消失；點擊新增列/欄，確認表格正確變化
  - 編輯器下方字數統計隨輸入即時更新
  - 點擊插入圖片、選擇本機圖片檔案，確認圖片插入且預設置中、100% 寬度；選取圖片後工具列切換成對齊+尺寸專屬列，切換對齊與尺寸按鈕確認圖片正確變化；點掉選取後工具列恢復正常
  - 插入圖表（既有功能）行為不變
