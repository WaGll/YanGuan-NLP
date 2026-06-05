<template>
  <div class="stat-card" :class="{ 'stat-card--clickable': !!$attrs.onClick }">
    <div class="stat-card__content">
      <div class="stat-card__icon-wrap">
        <el-icon :size="20">
          <component :is="icon" />
        </el-icon>
      </div>
      <div class="stat-card__text">
        <div class="stat-card__value">{{ displayValue }}</div>
        <div class="stat-card__label">{{ title }}</div>
      </div>
      <div class="stat-card__arrow" v-if="!!$attrs.onClick">
        <el-icon :size="16"><ArrowRight /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * StatCard — 研观统计卡片
 *
 * 设计特点：纯白底 + 24px 大圆角 + 薄荷绿图标圆背景 + 加粗指标数值。
 * 无阴影、无边线、右上角跳转箭头 (↗)。
 */
import { ArrowRight } from '@element-plus/icons-vue'
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: string | number
  icon: string
  color?: string
}>()

const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})
</script>

<style scoped>
.stat-card {
  position: relative;
  border-radius: 24px;
  background: #FFFFFF;
  padding: 24px;
  cursor: default;
  transition: all 0.25s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 109, 68, 0.06);
}

.stat-card--clickable {
  cursor: pointer;
}

.stat-card__content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

/* Icon badge — mint green semi-transparent circle */
.stat-card__icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(166, 231, 201, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card__icon-wrap :deep(.el-icon) {
  color: #006D44;
}

/* Text */
.stat-card__text {
  flex: 1;
  min-width: 0;
}

.stat-card__value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
  color: #1E2825;
}

.stat-card__label {
  font-size: 13px;
  color: #88918E;
  margin-top: 4px;
  font-weight: 500;
}

/* Arrow (top-right) */
.stat-card__arrow {
  color: #D8DDDB;
  flex-shrink: 0;
  margin-top: 4px;
  transition: color 0.2s ease;
}

.stat-card:hover .stat-card__arrow {
  color: #006D44;
}
</style>
