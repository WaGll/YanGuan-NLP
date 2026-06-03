<template>
  <el-card class="stat-card" shadow="hover">
    <div class="stat-card__inner">
      <div class="stat-card__icon" :style="{ color: color }">
        <el-icon :size="36">
          <component :is="icon" />
        </el-icon>
      </div>
      <div class="stat-card__body">
        <div class="stat-card__value" :style="{ color: color }">{{ value }}</div>
        <div class="stat-card__label">{{ title }}</div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  icon: string
  color?: string
}>()
</script>

<style scoped>
.stat-card {
  text-align: center;
  cursor: default;
}

.stat-card__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.stat-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-card__body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-card__value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-card__label {
  font-size: 14px;
  color: var(--text-secondary);
}
</style>
