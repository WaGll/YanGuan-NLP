<template>
  <el-drawer
    :model-value="visible"
    @update:model-value="$emit('close')"
    direction="rtl"
    size="560px"
    :before-close="() => $emit('close')"
  >
    <template #header v-if="topic">
      <div class="drawer-header">
        <span class="drawer-header__index">Topic {{ String(topic.topic.topic_index).padStart(2, '0') }}</span>
        <h3 class="drawer-header__title">
          {{ topic.topic.business_label || topic.topic.label || `Topic ${topic.topic.topic_index}` }}
        </h3>
      </div>
    </template>

    <template v-if="topic">
      <div class="drawer-body">
        <!-- Stats -->
        <section class="drawer-section">
          <h4 class="drawer-section__title">Overview</h4>
          <div class="drawer-stats-row">
            <div class="drawer-stat">
              <span class="drawer-stat__value">{{ topic.topic.doc_count.toLocaleString() }}</span>
              <span class="drawer-stat__label">Documents</span>
            </div>
            <div class="drawer-stat">
              <span class="drawer-stat__value">{{ topic.topic.coherence_score?.toFixed(3) ?? '--' }}</span>
              <span class="drawer-stat__label">Coherence</span>
            </div>
            <div class="drawer-stat">
              <span class="drawer-stat__value">{{ topic.keyword_count }}</span>
              <span class="drawer-stat__label">Keywords</span>
            </div>
          </div>
        </section>

        <!-- Keywords -->
        <section class="drawer-section">
          <h4 class="drawer-section__title">Keywords</h4>
          <div class="drawer-keywords">
            <span
              v-for="kw in topic.topic.keywords"
              :key="kw.word"
              class="drawer-keyword"
              :style="{ fontSize: `${Math.max(11, 11 + kw.weight * 6)}px` }"
            >
              {{ kw.word }}
              <sup class="drawer-keyword__weight">{{ kw.weight.toFixed(2) }}</sup>
            </span>
          </div>
        </section>

        <!-- Representative Comments -->
        <section v-if="topic.representative_comments.length > 0" class="drawer-section">
          <h4 class="drawer-section__title">Representative Comments</h4>
          <div class="drawer-comments">
            <blockquote
              v-for="(comment, idx) in topic.representative_comments.slice(0, 5)"
              :key="idx"
              class="drawer-comment"
            >
              {{ comment }}
            </blockquote>
          </div>
        </section>

        <!-- Sentiment Breakdown (donut) -->
        <section v-if="sentimentData" class="drawer-section">
          <h4 class="drawer-section__title">Sentiment Breakdown</h4>
          <div ref="sentimentChartRef" class="drawer-chart"></div>
        </section>

        <!-- Topic Trend (line chart) -->
        <section v-if="trendData && trendData.length > 0" class="drawer-section">
          <h4 class="drawer-section__title">Topic Trend</h4>
          <div ref="trendChartRef" class="drawer-chart drawer-chart--tall"></div>
        </section>
      </div>
    </template>

    <!-- Empty state -->
    <template v-else>
      <div class="drawer-empty">
        <p>No topic selected.</p>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { TopicDetail } from '@/types/topics'

const props = defineProps<{
  visible: boolean
  topic: TopicDetail | null
  sentimentData?: { positive: number; neutral: number; negative: number } | null
  trendData?: { date: string; value: number }[] | null
}>()

defineEmits<{
  close: []
}>()

const sentimentChartRef = ref<HTMLDivElement | null>(null)
const trendChartRef = ref<HTMLDivElement | null>(null)

let sentimentChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

// ── Sentiment donut ──
function renderSentimentChart() {
  if (!sentimentChartRef.value || !props.sentimentData) return

  if (!sentimentChart) {
    sentimentChart = echarts.init(sentimentChartRef.value)
  }

  const { positive, neutral, negative } = props.sentimentData

  sentimentChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#f0f1f3',
      textStyle: { color: '#1e293b', fontSize: 12 },
    },
    series: [{
      type: 'pie',
      radius: ['55%', '78%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderColor: '#ffffff', borderWidth: 2, borderRadius: 4 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
        scaleSize: 8,
      },
      data: [
        { value: positive, name: 'Positive', itemStyle: { color: '#16a34a' } },
        { value: neutral, name: 'Neutral', itemStyle: { color: '#f59e0b' } },
        { value: negative, name: 'Negative', itemStyle: { color: '#ef4444' } },
      ],
    }],
  })

  sentimentChart.resize()
}

// ── Topic trend line ──
function renderTrendChart() {
  if (!trendChartRef.value || !props.trendData || props.trendData.length === 0) return

  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const dates = props.trendData.map(d => d.date)
  const values = props.trendData.map(d => d.value)

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#f0f1f3',
      textStyle: { color: '#1e293b', fontSize: 12 },
    },
    grid: {
      top: 16,
      right: 16,
      bottom: 32,
      left: 40,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
    },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: '#16a34a', width: 2 },
      itemStyle: { color: '#16a34a' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(22, 163, 74, 0.12)' },
          { offset: 1, color: 'rgba(22, 163, 74, 0)' },
        ]),
      },
    }],
  })

  trendChart.resize()
}

// ── Watchers ──
watch(() => props.visible, async (isVisible) => {
  if (isVisible) {
    await nextTick()
    setTimeout(() => {
      renderSentimentChart()
      renderTrendChart()
    }, 100)
  }
})

watch(() => props.topic, () => {
  if (props.visible) {
    setTimeout(() => {
      renderSentimentChart()
      renderTrendChart()
    }, 100)
  }
})
</script>

<style scoped>
/* ── Header ── */
.drawer-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-header__index {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.drawer-header__title {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  letter-spacing: -0.2px;
}

/* ── Body ── */
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* ── Section ── */
.drawer-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.drawer-section__title {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0;
}

/* ── Stats row ── */
.drawer-stats-row {
  display: flex;
  gap: 24px;
}

.drawer-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-stat__value {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.drawer-stat__label {
  font-size: 11px;
  color: #94a3b8;
}

/* ── Keywords ── */
.drawer-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: baseline;
}

.drawer-keyword {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
}

.drawer-keyword__weight {
  font-size: 0.75em;
  color: #94a3b8;
  font-weight: 400;
  margin-left: 1px;
}

/* ── Comments ── */
.drawer-comments {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.drawer-comment {
  padding: 12px 16px;
  border-left: 2px solid #dcfce7;
  background: #fafbfc;
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
  margin: 0;
  font-style: normal;
}

/* ── Charts ── */
.drawer-chart {
  width: 100%;
  height: 200px;
}

.drawer-chart--tall {
  height: 240px;
}

/* ── Empty ── */
.drawer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #94a3b8;
  font-size: 14px;
}
</style>
