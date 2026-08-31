<template>
  <section class="workflow-page">
    <HubSidebar />

    <div class="workflow-page__main">
      <WorkflowWorkspace class="workflow-page__workspace" />
    </div>
  </section>
</template>

<script setup lang="ts">
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import WorkflowWorkspace from '@/components/workflow/WorkflowWorkspace.vue'
</script>

<style scoped>
.workflow-page {
  height: 100vh;
  display: flex;
  overflow: hidden;
  /* 半透明罩，把底下的全域漸層壓淡。畫布不鋪底色、整片漸層會直接曝在畫面上，
     Hub 那邊的濃度在這裡太重。蓋在整頁而不是只蓋主內容區，
     否則側邊欄那條會留在原濃度，兩邊之間出現接縫。
     濃度與顏色由 --canvas-veil 決定，深色是黑罩而不是白罩 */
  background: var(--canvas-veil);
}

.workflow-page__main {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
}

.workflow-page__workspace {
  height: 100%;
  overflow: hidden;
}
</style>
