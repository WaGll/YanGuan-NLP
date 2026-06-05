<template>
  <div class="dashboard-page">
    <!-- Error -->
    <el-alert
      v-if="dashboardStore.error"
      :title="dashboardStore.error"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- Row 1: KPI Cards -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :xs="12" :sm="6" v-for="card in statCards" :key="card.label">
        <KpiCard
          :label="card.label"
          :value="card.value"
          :caption="card.caption"
          :loading="dashboardStore.loading"
        />
      </el-col>
    </el-row>

    <!-- Row 2: Sentiment Trend + Donut -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :xs="24" :lg="16">
        <div class="dash-card dash-card--chart">
          <SectionHeader title="Sentiment Trend">
            <template #actions>
              <span class="dash-pill">Monthly</span>
            </template>
          </SectionHeader>
          <div ref="trendChartRef" class="trend-chart"></div>
        </div>
      </el-col>
      <el-col :xs="24" :lg="8">
        <div class="dash-card dash-card--chart">
          <SectionHeader title="Sentiment" />
          <SentimentPieChart :data="sentimentBins" />
        </div>
      </el-col>
    </el-row>

    <!-- Row 3: Top Keywords -->
    <div class="dash-card dash-card--chart">
      <SectionHeader title="Top Keywords" />
      <KeywordBarChart :data="keywordItems" />
    </div>

    <!-- Row 4: Keyword Cloud -->
    <div class="dash-card" v-if="wordcloudData.length > 0">
      <SectionHeader title="Keyword Cloud" />
      <WordCloudChart :data="wordcloudData" :max-words="80" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useDashboardStore } from '@/stores/dashboard'
import { fetchSentiment } from '@/api/sentiment'
import { fetchKeywords, fetchWordcloudData } from '@/api/keywords'
import { getTrends } from '@/api/trends'
import type { SentimentBin } from '@/api/sentiment'
import type { KeywordItem, WordcloudItem } from '@/api/keywords'
import KpiCard from '@/components/common/KpiCard.vue'
import SectionHeader from '@/components/common/SectionHeader.vue'
import SentimentPieChart from '@/components/charts/SentimentPieChart.vue'
import KeywordBarChart from '@/components/charts/KeywordBarChart.vue'
import WordCloudChart from '@/components/charts/WordCloudChart.vue'

const dashboardStore = useDashboardStore()
const trendChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null

const sentimentBins = ref<SentimentBin[]>([])
const keywordItems = ref<KeywordItem[]>([])
const wordcloudData = ref<WordcloudItem[]>([])

// ── KPI cards ──
const statCards = computed(() => {
  const s = dashboardStore.stats
  const positive = sentimentBins.value.find((b) =>
    b.label === '积极' || b.label === '正面' || b.label === 'positive' || b.label === 'Positive')
  return [
    { label: 'Comments',  value: s?.total_comments?.toLocaleString() ?? '--', caption: 'total' },
    { label: 'Positivity', value: positive ? `${positive.percentage}%` : '--', caption: 'positive sentiment' },
    { label: 'Topics',    value: '14', caption: 'BERTopic themes' },
    { label: 'Keywords',  value: '4,500+', caption: 'tokenized' },
  ]
})

// ── Trend chart ──
async function renderTrendChart() {
  if (!trendChartRef.value) return
  try {
    const data = await getTrends('sentiment', 'month')
    if (!trendChart) trendChart = echarts.init(trendChartRef.value)

    const dates = data.buckets.map((b) => b.bucket_start.slice(0, 7))
    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#f0f1f3',
        textStyle: { color: '#1e293b', fontSize: 12 },
      },
      legend: {
        data: ['Positive', 'Neutral', 'Negative'],
        top: 0,
        textStyle: { color: '#64748b', fontSize: 11 },
      },
      grid: { top: 32, right: 24, bottom: 32, left: 48 },
      xAxis: {
        type: 'category', data: dates,
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisTick: { show: false },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
      },
      series: [
        {
          name: 'Positive', type: 'line', data: data.buckets.map((b) => b.positive_count),
          smooth: true, symbolSize: 3, lineStyle: { color: '#16a34a', width: 2 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(22,163,74,0.1)' }, { offset: 1, color: 'rgba(22,163,74,0)' }]) },
        },
        {
          name: 'Neutral', type: 'line', data: data.buckets.map((b) => b.neutral_count),
          smooth: true, symbolSize: 3, lineStyle: { color: '#f59e0b', width: 2 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245,158,11,0.1)' }, { offset: 1, color: 'rgba(245,158,11,0)' }]) },
        },
        {
          name: 'Negative', type: 'line', data: data.buckets.map((b) => b.negative_count),
          smooth: true, symbolSize: 3, lineStyle: { color: '#ef4444', width: 2 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(239,68,68,0.1)' }, { offset: 1, color: 'rgba(239,68,68,0)' }]) },
        },
      ],
    })
    trendChart.resize()
  } catch { /* trends unavailable */ }
}

// ── Init ──
onMounted(async () => {
  await dashboardStore.fetchStats()

  try { const r = await fetchSentiment(); sentimentBins.value = r.bins }
  catch { sentimentBins.value = [
    { label: '正面', count: 0, percentage: 0 },
    { label: '中性', count: 0, percentage: 0 },
    { label: '负面', count: 0, percentage: 0 },
  ]}

  try { keywordItems.value = await fetchKeywords('frequency', 20) }
  catch { keywordItems.value = [] }

  try { wordcloudData.value = await fetchWordcloudData() }
  catch { wordcloudData.value = [] }

  await nextTick()
  await renderTrendChart()
  window.addEventListener('resize', () => trendChart?.resize())
})

onUnmounted(() => { trendChart?.dispose() })
</script>

<style scoped>
/* ── Card (v2: 24px radius, no border, soft shadow) ── */
.dash-card {
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  padding: 24px 28px;
  margin-bottom: 20px;
}

.dash-card--chart {
  min-height: 340px;
  display: flex;
  flex-direction: column;
}

.dash-pill {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 2px 10px;
  border-radius: 9999px;
  font-weight: 500;
}

.trend-chart {
  width: 100%;
  height: 340px;
}
</style>
