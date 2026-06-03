<template>
  <el-card>
    <el-skeleton :rows="rows" animated />
  </el-card>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  rows?: number
}>(), {
  rows: 4,
})
</script>
