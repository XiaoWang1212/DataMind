<template>
  <div class="icon-node-wrap">
    <Handle class="invisible-handle" :position="Position.Top" type="target" />
    <Handle class="invisible-handle" :position="Position.Right" type="source" />
    <Handle
      class="invisible-handle"
      :position="Position.Bottom"
      type="source"
    />
    <Handle class="invisible-handle" :position="Position.Left" type="target" />

    <div class="icon-node" :class="colorClass">
      <v-icon :icon="icon" size="26" />
    </div>
    <div class="icon-node-label">{{ label }}</div>
  </div>
</template>

<script setup lang="ts">
  import { Handle, type NodeProps, Position } from '@vue-flow/core'
  import { computed } from 'vue'

  const props = defineProps<NodeProps>()

  const icon = computed(() => String(props.data?.icon ?? 'mdi-circle'))
  const label = computed(() => String(props.data?.label ?? ''))
  const colorClass = computed(() =>
    String(props.data?.colorClass ?? 'node-purple'),
  )
</script>

<style scoped>
  .icon-node-wrap {
    position: relative;
    width: 94px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .icon-node {
    width: 56px;
    height: 56px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }

  .icon-node-label {
    margin-top: 10px;
    text-align: center;
    font-size: 15px;
    line-height: 1.15;
    color: #242424;
    white-space: pre-line;
  }

  .node-yellow {
    background: #e7d34f;
  }

  .node-purple {
    background: #bec5e3;
  }

  .invisible-handle {
    opacity: 0;
    width: 8px;
    height: 8px;
    border: none;
    background: transparent;
  }
</style>
