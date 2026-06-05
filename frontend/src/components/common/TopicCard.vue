<template>
  <div
    class="topic-card"
    :class="{ 'topic-card--loading': loading }"
    @click="!loading && $emit('click', topic!)"
  >
    <template v-if="!loading && topic">
      <!-- Header -->
      <div class="topic-card__header">
        <span class="topic-card__index">Topic {{ String(topic.topic_index).padStart(2, '0') }}</span>
        <span class="topic-card__label">{{ topic.business_label || topic.label || `Topic ${topic.topic_index}` }}</span>
      </div>

      <!-- Keywords -->
      <div class="topic-card__keywords">
        <span
          v-for="kw in displayKeywords"
          :key="kw.word"
          class="topic-card__keyword"
        >{{ kw.word }}</span>
      </div>

      <!-- Stats bar -->
      <div class="topic-card__stats">
        <span class="topic-card__stat">
          {{ topic.doc_count.toLocaleString() }} docs
        </span>
        <span v-if="topic.coherence_score != null" class="topic-card__stat">
          C: {{ topic.coherence_score.toFixed(2) }}
        </span>
      </div>
    </template>

    <template v-else>
      <div class="topic-card__skeleton-index"></div>
      <div class="topic-card__skeleton-label"></div>
      <div class="topic-card__skeleton-keywords">
        <span v-for="n in 4" :key="n" class="topic-card__skeleton-tag"></span>
      </div>
      <div class="topic-card__skeleton-stats"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TopicItem } from '@/types/topics'

const props = defineProps<{
  topic?: TopicItem | null
  loading?: boolean
}>()

defineEmits<{
  click: [topic: TopicItem]
}>()

const displayKeywords = computed(() => {
  if (!props.topic?.keywords) return []
  return props.topic.keywords.slice(0, 6)
})
</script>

<style scoped>
.topic-card {
  background: #ffffff;
  border: none;
  border-radius: 24px;
  padding: 24px 28px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.topic-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
  outline: 2px solid #16a34a;
  outline-offset: -2px;
}

/* ── Header ── */
.topic-card__header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.topic-card__index {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.topic-card__label {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.3;
}

/* ── Keywords ── */
.topic-card__keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.topic-card__keyword {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
  font-weight: 500;
  line-height: 1.5;
}

/* ── Stats ── */
.topic-card__stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.topic-card__stat {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

/* ── Skeleton ── */
.topic-card--loading {
  pointer-events: none;
}

.topic-card__skeleton-index {
  width: 50px;
  height: 10px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.topic-card__skeleton-label {
  width: 70%;
  height: 15px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.topic-card__skeleton-keywords {
  display: flex;
  gap: 4px;
}

.topic-card__skeleton-tag {
  width: 40px;
  height: 20px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.topic-card__skeleton-stats {
  width: 55%;
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
