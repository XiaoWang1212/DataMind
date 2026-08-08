# Hub Sidebar 毛玻璃質感

## 背景

透過視覺化 mockup 反覆比較後，確定了 Hub 側邊欄（`HubSidebar.vue`）的毛玻璃視覺方向：半透明模糊玻璃質感、背後透出品牌琥珀色系的柔和光暈球、玻璃邊緣反光、以及一道週期性掃過的光澤動畫。參考來源之一是 21st.dev 上的「Glass Shine Card」社群元件範例（色系與光暈球做法改用本專案既有的品牌琥珀色，未沿用該範例原本的粉橘配色）。

原本討論過讓 sidebar 真正脫離文件流、漂浮在主內容上方（`position: fixed`），但這需要把展開/收合狀態從 `HubSidebar.vue` 提升到 `HubLayout.vue`（因為主內容區的左邊距需要跟著 sidebar 寬度同步），改動範圍較大。後來發現不需要真的讓 sidebar 脫離版面就能做出一樣的玻璃質感：sidebar 維持現在跟主內容並排的 flex 版面與現有的展開/收合邏輯完全不動，只把它的背景換成半透明+模糊，並在它後面加一層固定定位、純裝飾用（不可互動）的光暈球圖層。玻璃因為背後有東西可以模糊而產生質感，展開/收合按鈕的程式邏輯不用改一行。

## 目標

1. `HubSidebar.vue` 的背景從不透明白底改成半透明玻璃（`backdrop-filter: blur`），加上邊緣反光（頂部亮邊）與週期性光澤掃過動畫
2. `HubLayout.vue` 新增一層固定定位的裝飾用光暈球（3 顆模糊的琥珀色圓形），位置對應 sidebar 左側區域，讓玻璃有東西可以透出來模糊
3. 光暈球圖層的寬度要能跟著 sidebar 展開/收合狀態自動收窄，避免收合時光暈球在窄版 sidebar 之外露出未被玻璃覆蓋的色塊——用純 CSS 手足選擇器（sibling combinator）做，不寫任何 JavaScript 狀態同步

## 非目標

- 不改變 `HubSidebar.vue` 現有的展開/收合互動邏輯、`collapsed` 狀態管理方式
- 不改變 `HubLayout.vue`、`HubSidebar.vue` 之間現有的元件溝通方式（不新增 props/emit/v-model）
- 不處理 `HubSidebar.vue` 以外的其他頁面/元件的玻璃化——這次範圍只有 Hub 側邊欄
- 不追求跟 21st.dev 範例逐像素一致，色系與造型都已經改成符合本專案品牌色（琥珀 `--color-accent`）與現有排版比例

## 設計

### 段落 A：`HubLayout.vue` 新增裝飾用光暈球圖層

在 `<HubSidebar />` 之後（DOM 順序上是 sidebar 的手足元素，這點很重要，見段落 C 的收合連動選擇器）加入一個不可互動的裝飾容器：

```html
<div class="hub-wrap">
  <HubSidebar />
  <div aria-hidden="true" class="hub-glass-orbs">
    <div class="orb orb-1" />
    <div class="orb orb-2" />
    <div class="orb orb-3" />
  </div>
  <main class="hub-main">
    <RouterView />
  </main>
</div>
```

```css
.hub-glass-orbs {
  position: fixed;
  top: 0;
  left: 0;
  width: 210px;
  height: 100vh;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
  transition: width 0.2s ease;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(38px);
}

.orb-1 {
  width: 160px;
  height: 160px;
  top: -40px;
  left: -30px;
  background: radial-gradient(circle, var(--color-accent) 0%, transparent 70%);
  opacity: 0.55;
}

.orb-2 {
  width: 130px;
  height: 130px;
  top: 260px;
  left: 40px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-accent) 60%, white) 0%, transparent 70%);
  opacity: 0.5;
}

.orb-3 {
  width: 110px;
  height: 110px;
  top: 480px;
  left: -20px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-accent) 85%, black) 0%, transparent 70%);
  opacity: 0.35;
}
```

210px 對應 sidebar 展開時的寬度。`pointer-events: none` 確保這層不會擋到任何點擊。

### 段落 B：`HubSidebar.vue` 玻璃化

```css
/* 現在 */
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: var(--color-surface);
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
}
```

```css
/* 改為 */
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-top: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.25),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    4px 0 24px rgba(28, 33, 48, 0.1);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 2;
}
```

`position: sticky` 維持不變（不改成 `fixed`）——`z-index: 2` 確保它蓋在段落 A 的光暈球圖層（`z-index: 0`）之上。原本的 `border-right: 1px solid #e8e8e8` 拿掉，改用 `box-shadow` 做邊緣反光與投影，視覺上仍然能區分 sidebar 與主內容區的邊界。

在 `.hub-sidebar` 規則後面加入光澤掃過的偽元素：

```css
.hub-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 70%;
  height: 220%;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 255, 255, 0.7) 50%, transparent 65%);
  transform: translate(-160%, -20%) rotate(12deg);
  animation: hub-sidebar-shine 4.5s ease-in-out infinite;
  pointer-events: none;
  z-index: 1;
}

@keyframes hub-sidebar-shine {
  0%, 25% {
    transform: translate(-160%, -20%) rotate(12deg);
  }
  65%, 100% {
    transform: translate(160%, -20%) rotate(12deg);
  }
}
```

`.hub-sidebar-header`、`.hub-nav`、`.hub-sidebar-footer` 這三個既有子元素要各自加上 `position: relative; z-index: 2;`，確保排在光澤偽元素（`z-index: 1`）之上，不會被蓋住或影響點擊。

### 段落 C：收合時光暈球圖層跟著收窄（純 CSS，不寫 JS）

`HubSidebar.vue` 收合時，根元素會多一個 `hub-sidebar--collapsed` class（既有邏輯，不用動）。利用 Vue scoped CSS 的規則——子元件的根節點會同時帶有父層與自己的 scope 屬性——在 `HubLayout.vue` 的 `<style scoped>` 裡可以直接用手足選擇器接住這個 class：

```css
.hub-sidebar--collapsed ~ .hub-glass-orbs {
  width: 56px;
}
```

56px 對應 `.hub-sidebar--collapsed` 收合後的寬度（`HubSidebar.vue` 裡既有定義）。收窄後三顆光暈球有部分會被裁掉（`.hub-glass-orbs` 有 `overflow: hidden`），但保留在可見範圍內的部分仍會被收合後的玻璃 sidebar 蓋住，不會露出未遮蔽的色塊。

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 開啟任一 Hub 頁面（例如 `/hub/dashboard`），確認：sidebar 呈現半透明模糊玻璃質感、背後隱約看得到琥珀色光暈、頂部有一道亮邊、每隔幾秒有光澤掃過動畫
- 點擊收合按鈕，確認 sidebar 收合到 56px 寬時，玻璃質感與光暈仍正常，主內容區不受影響，也沒有露出未被遮蔽的光暈色塊
- 確認 nav 項目（儀表板/框架庫/專案/設定）在光澤動畫掃過時仍可正常點擊、文字清晰可讀
