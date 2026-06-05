<template>
  <el-card class="loading-card">
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

<style scoped>
.loading-card {
  border-radius: 24px;
}

.loading-card :deep(.el-skeleton__item) {
  border-radius: 12px;
  background: linear-gradient(90deg, #F4F7F6 25%, #E8F9F1 50%, #F4F7F6 75%);
}
</style>
