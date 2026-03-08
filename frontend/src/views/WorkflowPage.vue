<template>
  <section class="workflow-page">
    <WorkflowWorkspace class="workflow-page__workspace" />
  </section>
</template>

<script setup lang="ts">
import WorkflowWorkspace from '@/components/workflow/WorkflowWorkspace.vue'
</script>

<style scoped>
.workflow-page {
  height: 100vh;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
  background-color: #f9fbff;
}

.workflow-page__workspace {
  height: 100%;
  overflow: hidden;
}
</style>