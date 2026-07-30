# 前端 UX 修正：Sidebar Hover、論文編輯工具列

## 背景

使用者回報三個具體問題，另外還提出一個範圍開放的「增加可讀性及設計感」大目標。經討論後，本輪先處理三個已定位根因、範圍明確的具體問題；「可讀性及設計感」留給後續另一輪獨立討論。

## 目標

1. 修正 Hub 側邊欄導覽項目 hover 時對比度過低、視覺上像「消失」的問題
2. 論文編輯模式下，若沒有任何未儲存的修改，允許直接用「檢視」切換鈕退出編輯模式，不必強制點選「取消」
3. 修正論文編輯工具列的「取消」「儲存」按鈕出現/消失時造成的版面位移

## 非目標

- 不處理「增加可讀性及設計感」這個開放性大目標（留待後續獨立討論範圍）
- 不改動論文編輯模式下「有未儲存修改時」的既有鎖定行為（維持需要明確按「取消」或「儲存」）
- 不新增離開頁面（路由切換）時的未儲存變更警告
- 不改動 Hub 側邊欄以外的其他 hover 效果

## 設計

### 1. Sidebar hover 對比度

`frontend/src/components/hub/HubSidebar.vue`：

```css
/* 現況：hover 背景色跟側邊欄自身背景色幾乎相同，對比度不足 */
.hub-nav-item:hover {
  background: var(--color-primary); /* #f6f5f2，疊在 --color-surface #ffffff 上幾乎看不出來 */
}

/* 改為：淡琥珀色色塊，與選中狀態的實心 accent 呈現漸進關係 */
.hub-nav-item:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}
```

`.hub-toggle-btn:hover`（側邊欄摺疊按鈕）目前也是 `background: var(--color-primary)`，有相同的低對比問題，一併改成同樣的淡琥珀色塊，維持一致性：

```css
.hub-toggle-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}
```

### 2. 論文編輯：無修改即可直接退出

`frontend/src/views/PaperPage.vue` 新增一個「是否有未儲存修改」的判斷，並用它控制 `ModeSwitch` 的鎖定狀態：

```ts
const hasChanges = computed(() =>
  JSON.stringify(toRaw(report.value)) !== JSON.stringify(savedSnapshot),
)
```

（`report.value` 的三個欄位 `title`/`content`/`citations` 都是純 JSON 可序列化的資料——`content` 是 Tiptap 的 `JSONContent`、`citations` 是純物件陣列——用 `JSON.stringify` 比較是可靠且足夠簡單的做法，不需要額外的深比較函式庫。）

`ModeSwitch` 的 `locked` 綁定從：

```html
<ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
```

改成：

```html
<ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit' && hasChanges" />
```

行為結果：
- 進入編輯模式後，只要內容跟 `savedSnapshot` 完全一致（沒有任何修改），工具列上的「檢視」按鈕不再被鎖定，點擊可直接切回檢視模式（因為內容本就沒變，不需要額外呼叫 `cancelEdit()` 的重置邏輯，直接改 `mode` 即可，`ModeSwitch` 的 `update:modelValue` 事件已經是這樣運作）
- 只要有任何修改，「檢視」維持鎖定，使用者仍需明確點擊「取消」（放棄修改）或「儲存」——這部分行為不變

### 3. 取消/儲存按鈕造成的版面位移

`frontend/src/views/PaperPage.vue` 的 `.toolbar-actions` 區塊：

```html
<!-- 現況：v-if 讓按鈕在非編輯模式下完全不佔版面空間，
     切換到編輯模式時工具列寬度瞬間增加，把 ModeSwitch 往左推 -->
<template v-if="mode === 'edit'">
  <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
  <v-btn class="bg-accent" color="accent" :disabled="!projectId" :loading="saving" size="small" @click="save">
    儲存
  </v-btn>
</template>
```

改為按鈕永遠掛載在 DOM 上，用 CSS class 切換 `visibility: hidden`（而非 `v-if`／`v-show` 的 `display:none`），讓這塊區域的版面空間固定保留，`ModeSwitch` 的位置不再受影響：

```html
<div class="edit-actions" :class="{ 'edit-actions--hidden': mode !== 'edit' }">
  <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
  <v-btn class="bg-accent" color="accent" :disabled="!projectId" :loading="saving" size="small" @click="save">
    儲存
  </v-btn>
</div>
```

```css
.edit-actions--hidden {
  visibility: hidden;
  pointer-events: none;
}
```

`visibility: hidden` 的元素仍佔版面空間但不可見、不可互動，因此非編輯模式下按鈕不可見也不可點擊，但工具列整體寬度不會因為模式切換而改變。

## 驗證方式

- `npm run build`（`vue-tsc --build --force` + `vite build`）確認無編譯錯誤
- 瀏覽器 devtools：對 `.hub-nav-item:hover`、`.hub-toggle-btn:hover` 觸發 hover 狀態，確認 `getComputedStyle(...).backgroundColor` 與側邊欄背景色 `rgb(255,255,255)` 有明顯差異（非 `rgb(246,245,242)`）
- 手動測試：進入論文編輯模式、不做任何修改，點擊「檢視」確認可直接切回檢視模式；做出修改後再點擊「檢視」確認仍維持鎖定、需要「取消」或「儲存」才能離開
- 手動測試：切換檢視/編輯模式時，用瀏覽器 devtools 量測 `ModeSwitch` 元件（`.mode-switch`）的 `getBoundingClientRect().left`，確認切換前後數值不變（無位移）
