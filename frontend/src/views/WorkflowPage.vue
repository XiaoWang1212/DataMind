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
  background-color: #f9fbff;
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
