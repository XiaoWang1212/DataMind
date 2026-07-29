<template>
  <section class="workflow-page">
    <aside class="left-panel">
      <div class="brand-row">
        <v-icon class="brand-icon" icon="mdi-shimmer" size="20" />
        <span class="brand-text">DataMind</span>
      </div>

      <v-btn
        block
        class="new-btn"
        color="accent"
        prepend-icon="mdi-plus"
      >新增</v-btn>

      <div class="recent-title">最近使用</div>
      <div class="recent-list">
        <div class="recent-item active">
          <div class="item-title">XXXXXX</div>
          <div class="item-time">XX天前</div>
        </div>
        <div v-for="index in 5" :key="index" class="recent-item plain">
          <div class="item-title">XXXXXX</div>
          <div class="item-time">XX天前</div>
        </div>
      </div>

      <div class="user-box">
        <v-avatar color="accent" size="44">
          <v-icon icon="mdi-account" />
        </v-avatar>
        <div>
          <div class="user-name">使用者帳號</div>
          <div class="user-mail">user123@email.com</div>
        </div>
      </div>
    </aside>

    <main class="main-area">
      <div class="flow-area">
        <VueFlow
          :default-viewport="{ zoom: 1, x: 20, y: 20 }"
          :edges="edges"
          :elements-selectable="false"
          :fit-view-on-init="false"
          :max-zoom="1.25"
          :min-zoom="0.75"
          :node-types="nodeTypes"
          :nodes="nodes"
          :nodes-draggable="false"
          :pan-on-drag="false"
          :zoom-on-scroll="false"
        />
      </div>

      <div class="setting-area">
        <div class="tabs">
          <button class="tab active" type="button">基本設定</button>
          <button class="tab" type="button">資料處理</button>
          <button class="tab" type="button">模型選擇</button>
          <button class="tab" type="button">輸出設定</button>
        </div>

        <div class="form-board">
          <div class="field">目標變數</div>

          <div class="panel">
            <div class="panel-header">
              任務類型 <v-icon icon="mdi-chevron-down" size="20" />
            </div>
            <div class="panel-body" />
          </div>
        </div>
      </div>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { type Edge, type Node, VueFlow } from '@vue-flow/core'
  import { markRaw } from 'vue'
  import IconNode from '@/components/workflow/IconNode.vue'
  import '@vue-flow/core/dist/style.css'

  import '@vue-flow/core/dist/theme-default.css'

  const nodeTypes = {
    iconNode: markRaw(IconNode),
  }

  const nodes: Node[] = [
    {
      id: 'file',
      type: 'iconNode',
      position: { x: 40, y: 120 },
      data: {
        icon: 'mdi-file-outline',
        label: 'File',
        colorClass: 'node-yellow',
      },
    },
    {
      id: 'table',
      type: 'iconNode',
      position: { x: 220, y: 28 },
      data: {
        icon: 'mdi-table-large',
        label: 'Data Table',
        colorClass: 'node-yellow',
      },
    },
    {
      id: 'distribution',
      type: 'iconNode',
      position: { x: 220, y: 120 },
      data: {
        icon: 'mdi-chart-histogram',
        label: 'Distribution',
        colorClass: 'node-yellow',
      },
    },
    {
      id: 'intent',
      type: 'iconNode',
      position: { x: 135, y: 252 },
      data: {
        icon: 'mdi-crosshairs-gps',
        label: 'Intent &\nTarget',
        colorClass: 'node-yellow',
      },
    },
    {
      id: 'preprocess',
      type: 'iconNode',
      position: { x: 395, y: 244 },
      data: {
        icon: 'mdi-filter-variant',
        label: 'Preprocesses',
        colorClass: 'node-purple',
      },
    },
    {
      id: 'lr',
      type: 'iconNode',
      position: { x: 615, y: 28 },
      data: {
        icon: 'mdi-chart-line',
        label: 'Logistic\nRegression',
        colorClass: 'node-purple',
      },
    },
    {
      id: 'rf',
      type: 'iconNode',
      position: { x: 620, y: 150 },
      data: {
        icon: 'mdi-source-branch',
        label: 'Random\nForest',
        colorClass: 'node-purple',
      },
    },
    {
      id: 'nb',
      type: 'iconNode',
      position: { x: 620, y: 272 },
      data: {
        icon: 'mdi-format-align-center',
        label: 'Naive\nBayes',
        colorClass: 'node-purple',
      },
    },
    {
      id: 'score',
      type: 'iconNode',
      position: { x: 820, y: 165 },
      data: {
        icon: 'mdi-test-tube',
        label: 'Test &\nScore',
        colorClass: 'node-purple',
      },
    },
    {
      id: 'matrix',
      type: 'iconNode',
      position: { x: 1018, y: 82 },
      data: {
        icon: 'mdi-table',
        label: 'Confusion\nMatrix',
        colorClass: 'node-purple',
      },
    },
    {
      id: 'predict',
      type: 'iconNode',
      position: { x: 1018, y: 246 },
      data: {
        icon: 'mdi-head-sync',
        label: 'Predictions',
        colorClass: 'node-purple',
      },
    },
  ]

  const edges: Edge[] = [
    {
      id: 'e-file-table',
      source: 'file',
      target: 'table',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-file-dist',
      source: 'file',
      target: 'distribution',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-file-intent',
      source: 'file',
      target: 'intent',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-intent-pre',
      source: 'intent',
      target: 'preprocess',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-pre-lr',
      source: 'preprocess',
      target: 'lr',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-pre-rf',
      source: 'preprocess',
      target: 'rf',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-pre-nb',
      source: 'preprocess',
      target: 'nb',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-lr-score',
      source: 'lr',
      target: 'score',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-rf-score',
      source: 'rf',
      target: 'score',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-nb-score',
      source: 'nb',
      target: 'score',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-score-matrix',
      source: 'score',
      target: 'matrix',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
    {
      id: 'e-score-predict',
      source: 'score',
      target: 'predict',
      animated: false,
      style: { stroke: '#c9c9c9', strokeWidth: 1.5 },
    },
  ]
</script>

<style scoped>
  .workflow-page {
    height: calc(100vh - 64px);
    display: flex;
    background: #f5f5f7;
  }

  .left-panel {
    width: 250px;
    border-right: 1px solid #d9d9d9;
    background: #f4f4f6;
    display: flex;
    flex-direction: column;
    padding: 22px 20px;
  }

  .brand-row {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #0f56ca;
    font-size: 40px;
    font-weight: 700;
  }

  .brand-icon {
    color: #0f56ca;
  }

  .brand-text {
    font-size: 40px;
    line-height: 1;
  }

  .new-btn {
    margin-top: 18px;
    border-radius: 10px;
    height: 52px;
    font-size: 34px;
    font-weight: 700;
    letter-spacing: 0;
  }

  .recent-title {
    margin-top: 24px;
    color: #6c6f78;
    font-size: 31px;
    font-weight: 500;
  }

  .recent-list {
    margin-top: 8px;
    flex: 1;
    overflow: auto;
  }

  .recent-item {
    padding: 12px 14px;
    border-radius: 12px;
    margin-bottom: 12px;
  }

  .recent-item.active {
    background: #dce8f8;
    border: 1px solid #8bb2ef;
  }

  .recent-item.plain {
    border: 1px solid transparent;
  }

  .item-title {
    color: #0e4dae;
    font-size: 41px;
    font-weight: 700;
    line-height: 1.1;
  }

  .item-time {
    color: #0e4dae;
    font-size: 34px;
    line-height: 1.15;
  }

  .user-box {
    border-top: 1px solid #d9d9d9;
    margin: 0 -20px -22px;
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    background: #f0f1f4;
  }

  .user-name {
    color: #191b1f;
    font-size: 34px;
    font-weight: 700;
    line-height: 1.1;
  }

  .user-mail {
    color: #8b8d94;
    font-size: 20px;
  }

  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .flow-area {
    height: 52%;
    border-bottom: 1px solid #d9d9d9;
    background: #f6f6f8;
  }

  :deep(.vue-flow__pane) {
    cursor: default;
  }

  :deep(.vue-flow__edge-path) {
    stroke: #c9c9c9;
    stroke-width: 1.5;
  }

  .setting-area {
    flex: 1;
    background: #f9f9fb;
    padding: 16px 28px 22px;
    background-image: radial-gradient(#d8d8dd 1px, transparent 1px);
    background-size: 20px 20px;
  }

  .tabs {
    display: flex;
    align-items: center;
    gap: 42px;
    border-bottom: 1px solid #e2e2e7;
    padding: 0 8px 10px;
  }

  .tab {
    border: none;
    background: transparent;
    color: #202226;
    font-size: 30px;
    padding: 0 0 8px;
  }

  .tab.active {
    border-bottom: 3px solid #1f67df;
  }

  .form-board {
    margin: 22px auto 0;
    width: min(1120px, 100%);
  }

  .field {
    background: #f8f8fb;
    border: 1px solid #cfcfd6;
    border-radius: 12px;
    height: 64px;
    display: flex;
    align-items: center;
    padding: 0 22px;
    color: #222529;
    font-size: 30px;
  }

  .panel {
    margin-top: 16px;
    border: 1px solid #cfcfd6;
    border-radius: 12px;
    background: #f8f8fb;
    overflow: hidden;
  }

  .panel-header {
    height: 64px;
    border-bottom: 1px solid #cfcfd6;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 22px;
    color: #222529;
    font-size: 30px;
  }

  .panel-body {
    height: 180px;
  }

  @media (max-width: 1280px) {
    .left-panel {
      width: 220px;
    }

    .brand-text,
    .item-title,
    .user-name {
      font-size: 24px;
    }

    .new-btn,
    .tab,
    .field,
    .panel-header,
    .item-time {
      font-size: 18px;
    }

    .user-mail {
      font-size: 13px;
    }
  }
</style>
