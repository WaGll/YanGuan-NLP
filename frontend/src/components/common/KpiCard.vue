<template>
  <div class="kpi-card" :class="{ 'kpi-card--loading': loading }">
    <template v-if="!loading">
      <span class="kpi-card__label">{{ label }}</span>
      <span class="kpi-card__value">{{ formattedValue }}</span>
      <span v-if="caption" class="kpi-card__caption">{{ caption }}</span>
    </template>
    <template v-else>
      <div class="kpi-card__skeleton-label"></div>
      <div class="kpi-card__skeleton-value"></div>
      <div class="kpi-card__skeleton-caption"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  caption?: string
  loading?: boolean
}>(), {
  loading: false,
})

const formattedValue = computed(() => {
  const v = props.value
  if (typeof v === 'number') {
    return v.toLocaleString()
  }
  return v
})
</script>

<style scoped>
.kpi-card {
  background: #ffffff;
  border: none;
  border-radius: 24px;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.kpi-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.kpi-card__label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.kpi-card__value {
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.kpi-card__caption {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}

/* ── Skeleton ── */
.kpi-card--loading {
  pointer-events: none;
}

.kpi-card__skeleton-label {
  width: 60%;
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.kpi-card__skeleton-value {
  width: 45%;
  height: 32px;
  border-radius: 6px;
  margin: 4px 0;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.kpi-card__skeleton-caption {
  width: 35%;
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
