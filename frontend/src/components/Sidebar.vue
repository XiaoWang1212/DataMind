<template>
  <aside class="sidebar">
    <div class="logo">
      <span class="logo-icon">✨</span>
      <span class="logo-text">DataMind</span>
    </div>

    <button class="add-btn" @click="addNewItem">
      <span class="plus">+</span> 新增
    </button>

    <nav class="nav-container">
      <p class="section-title">最近使用</p>
      
      <div 
        v-for="(item, index) in historyItems" 
        :key="index"
        class="sidebar-item"
        :class="{ active: activeIndex === index }"
        @click="activeIndex = index"
      >
        <div class="item-info">
          <div v-if="editingIndex === index" class="edit-input">
            <input 
              v-model="editName" 
              @keyup.enter="saveEdit(index)" 
              @blur="saveEdit(index)" 
              @keyup.escape="cancelEdit" 
              ref="editInput"
              class="edit-field"
            />
          </div>
          <div v-else class="item-title">{{ item.name }}</div>
          <div class="item-date">{{ item.time }}</div>
        </div>
        <div class="more-options" @click.stop="toggleMenu(index)">⋮</div>
        
        <!-- 選單 -->
        <div v-if="openMenuIndex === index" class="menu-dropdown">
          <button class="menu-item" @click="startEdit(index)">編輯</button>
          <button class="menu-item delete" @click="deleteItem(index)">刪除</button>
        </div>
      </div>
    </nav>

    <div class="user-profile">
      <div class="avatar-circle">
        <span class="user-icon">👤</span>
      </div>
      <div class="user-details">
        <p class="user-name">{{ userName }}</p>
        <p class="user-email">{{ userEmail }}</p>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

// 控制目前選中的項目索引
const activeIndex = ref(0);

// 側邊欄資料
const historyItems = ref([
  { name: 'XXXXXX', time: 'XX天前' },
  { name: 'XXXXXX', time: 'XX天前' },
  { name: 'XXXXXX', time: 'XX天前' },
  { name: 'XXXXXX', time: 'XX天前' },
  { name: 'XXXXXX', time: 'XX天前' },
  { name: 'XXXXXX', time: 'XX天前' },
]);

// 控制選單打開的索引
const openMenuIndex = ref(-1);

// 編輯模式
const editingIndex = ref(-1);
const editName = ref('');

// 用戶資訊
const userName = ref('使用者帳號');
const userEmail = ref('user123@email.com');

// 處理點擊外部關閉選單
const handleClickOutside = (event) => {
  const menu = event.target.closest('.menu-dropdown');
  if (!menu) {
    openMenuIndex.value = -1;
  }
};

// 新增項目的簡單邏輯
const addNewItem = () => {
  historyItems.value.unshift({
    name: '新專案',
    time: '剛才'
  });
  activeIndex.value = 0; // 自動選中新建立的項目
};

// 切換選單
const toggleMenu = (index) => {
  openMenuIndex.value = openMenuIndex.value === index ? -1 : index;
};

// 開始編輯
const startEdit = (index) => {
  editingIndex.value = index;
  editName.value = historyItems.value[index].name;
  openMenuIndex.value = -1;
};

// 保存編輯
const saveEdit = (index) => {
  if (editName.value.trim()) {
    historyItems.value[index].name = editName.value.trim();
  }
  editingIndex.value = -1;
  editName.value = '';
};

// 取消編輯
const cancelEdit = () => {
  editingIndex.value = -1;
  editName.value = '';
};

// 刪除項目
const deleteItem = (index) => {
  historyItems.value.splice(index, 1);
  if (activeIndex.value >= index && activeIndex.value > 0) {
    activeIndex.value--;
  }
  openMenuIndex.value = -1;
};

// 組件掛載時添加事件監聽器
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

// 組件卸載時移除事件監聽器
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* 側邊欄整體容器 */
.sidebar {
  width: 260px;
  height: 100vh;
  background-color: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  box-sizing: border-box;
}

/* Logo 樣式 */
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 800;
  color: #1e40af;
  margin-bottom: 24px;
}

/* 按鈕樣式 */
.add-btn {
  background-color: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  margin-bottom: 32px;
}

.add-btn:hover {
  background-color: #1d4ed8;
}

/* 清單區域 */
.section-title {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 12px;
  padding-left: 8px;
}

.nav-container {
  flex-grow: 1;
  overflow-y: auto;
}

/* 項目樣式 (原本在子元件的內容) */
.sidebar-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 10px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  position: relative;
}

.sidebar-item:hover {
  background-color: #f3f4f6;
}

.sidebar-item.active {
  background-color: #eff6ff;
  border-color: #bfdbfe;
}

.item-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e3a8a;
}

.item-date {
  font-size: 12px;
  color: #6b7280;
}

.more-options {
  color: #9ca3af;
  font-size: 18px;
  cursor: pointer;
}

/* 編輯輸入 */
.edit-input {
  display: flex;
  align-items: center;
}

.edit-field {
  font-size: 16px;
  font-weight: 700;
  color: #1e3a8a;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  padding: 4px 8px;
  width: 100%;
  background-color: #eff6ff;
}

/* 選單樣式 */
.menu-dropdown {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  z-index: 10;
  min-width: 80px;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
}

.menu-item:hover {
  background-color: #f3f4f6;
}

.menu-item.delete {
  color: #dc2626;
}

.menu-item.delete:hover {
  background-color: #fef2f2;
}

/* 底部使用者區 */
.user-profile {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-circle {
  width: 40px;
  height: 40px;
  background-color: #2563eb;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: white;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: black;
}

.user-email {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}
</style>