<template>
  <div class="sentiment-page">
    <!-- Row 1: KPI Cards -->
    <el-row :gutter="20" style="margin-bottom: 28px">
      <el-col :xs="24" :sm="8" v-for="card in kpiCards" :key="card.label">
        <div class="sentiment-card">
          <span class="sentiment-card__label">{{ card.label }}</span>
          <span class="sentiment-card__value" :style="{ color: card.color }">{{ card.percentage }}%</span>
          <span class="sentiment-card__count">{{ card.count.toLocaleString() }} comments</span>
        </div>
      </el-col>
    </el-row>

    <!-- Row 2: Donut + Trend -->
    <el-row :gutter="20" style="margin-bottom: 28px">
      <el-col :xs="24" :lg="10">
        <div class="sentiment-card sentiment-card--chart">
          <h3 class="sentiment-card__title">SENTIMENT BREAKDOWN</h3>
          <SentimentPieChart :data="sentimentBins" />
        </div>
      </el-col>
      <el-col :xs="24" :lg="14">
        <div class="sentiment-card sentiment-card--chart">
          <h3 class="sentiment-card__title">SENTIMENT TREND</h3>
          <div ref="trendChartRef" class="trend-chart"></div>
        </div>
      </el-col>
    </el-row>

    <!-- Row 3: Distribution Table -->
    <div class="sentiment-card">
      <h3 class="sentiment-card__title">DISTRIBUTION</h3>
      <div class="dist-table">
        <div class="dist-table__header">
          <span class="dist-table__th">Category</span>
          <span class="dist-table__th">Count</span>
          <span class="dist-table__th" style="flex:1">Proportion</span>
        </div>
        <div
          v-for="bin in sentimentBins"
          :key="bin.label"
          class="dist-table__row"
        >
          <span class="dist-table__cell dist-table__cell--label">{{ bin.label }}</span>
          <span class="dist-table__cell dist-table__cell--count">{{ bin.count.toLocaleString() }}</span>
          <div class="dist-table__cell dist-table__cell--bar" style="flex:1">
            <div class="dist-bar">
              <div
                class="dist-bar__fill"
                :style="{
                  width: `${bin.percentage}%`,
                  background: getBarColor(bin.label),
                }"
              ></div>
            </div>
            <span class="dist-bar__pct">{{ bin.percentage }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useSentimentStore } from '@/stores/sentiment'
import { getTrends } from '@/api/trends'
import type { SentimentBin } from '@/api/sentiment'
import SentimentPieChart from '@/components/charts/SentimentPieChart.vue'

const sentimentStore = useSentimentStore()
const trendChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null

const sentimentBins = computed<SentimentBin[]>(() => sentimentStore.distribution?.bins ?? [])

const kpiCards = computed(() => {
  const bins = sentimentBins.value
  const positive = bins.find((b) => b.label === '积极' || b.label === '正面' || b.label === 'positive' || b.label === 'Positive')
  const neutral  = bins.find((b) => b.label === '中性' || b.label === 'neutral' || b.label === 'Neutral')
  const negative = bins.find((b) => b.label === '消极' || b.label === '负面' || b.label === 'negative' || b.label === 'Negative')
  return [
    { label: 'Positive', percentage: positive?.percentage ?? 0, count: positive?.count ?? 0, color: '#16a34a' },
    { label: 'Neutral',  percentage: neutral?.percentage  ?? 0, count: neutral?.count  ?? 0, color: '#f59e0b' },
    { label: 'Negative', percentage: negative?.percentage ?? 0, count: negative?.count ?? 0, color: '#ef4444' },
  ]
})

function getBarColor(label: string): string {
  if (label.includes('正面') || label.toLowerCase().includes('positive')) return '#16a34a'
  if (label.includes('中性') || label.toLowerCase().includes('neutral')) return '#f59e0b'
  return '#ef4444'
}

async function renderTrendChart() {
  if (!trendChartRef.value) return

  try {
    const data = await getTrends('sentiment', 'month')
    if (!trendChart) {
      trendChart = echarts.init(trendChartRef.value)
    }

    const dates = data.buckets.map((b) => b.bucket_start.slice(0, 7))
    const positiveData = data.buckets.map((b) => b.positive_count)
    const neutralData  = data.buckets.map((b) => b.neutral_count)
    const negativeData = data.buckets.map((b) => b.negative_count)

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
      grid: { top: 32, right: 24, bottom: 24, left: 48 },
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
      series: [
        {
          name: 'Positive', type: 'line', data: positiveData,
          smooth: true, symbolSize: 2, lineStyle: { color: '#16a34a', width: 2 },
          itemStyle: { color: '#16a34a' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(22,163,74,0.1)' }, { offset: 1, color: 'rgba(22,163,74,0)' }]) },
        },
        {
          name: 'Neutral', type: 'line', data: neutralData,
          smooth: true, symbolSize: 2, lineStyle: { color: '#f59e0b', width: 2 },
          itemStyle: { color: '#f59e0b' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(245,158,11,0.1)' }, { offset: 1, color: 'rgba(245,158,11,0)' }]) },
        },
        {
          name: 'Negative', type: 'line', data: negativeData,
          smooth: true, symbolSize: 2, lineStyle: { color: '#ef4444', width: 2 },
          itemStyle: { color: '#ef4444' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(239,68,68,0.1)' }, { offset: 1, color: 'rgba(239,68,68,0)' }]) },
        },
      ],
    })

    trendChart.resize()
  } catch {
    // Trends data unavailable — chart stays empty
  }
}

onMounted(async () => {
  await sentimentStore.fetchDistribution()
  await nextTick()
  await renderTrendChart()
  window.addEventListener('resize', () => trendChart?.resize())
})

onUnmounted(() => {
  trendChart?.dispose()
})
</script>

<style scoped>
/* ── Card (v2: 24px radius, no border, soft shadow) ── */
.sentiment-card {
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  padding: 24px 28px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sentiment-card--chart {
  min-height: 360px;
}

.sentiment-card__title {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 12px 0;
}

.sentiment-card__label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.sentiment-card__value {
  font-size: 32px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.sentiment-card__count {
  font-size: 12px;
  color: #94a3b8;
}

/* ── Trend chart ── */
.trend-chart {
  width: 100%;
  height: 300px;
  flex: 1;
}

/* ── Distribution table ── */
.dist-table {
  display: flex;
  flex-direction: column;
}

.dist-table__header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 12px;
}

.dist-table__th {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  width: 100px;
}

.dist-table__row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid #f8fafc;
}

.dist-table__cell {
  font-size: 13px;
}

.dist-table__cell--label {
  width: 100px;
  color: #1e293b;
  font-weight: 500;
}

.dist-table__cell--count {
  width: 100px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}

.dist-table__cell--bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dist-bar {
  flex: 1;
  height: 10px;
  background: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
}

.dist-bar__fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.dist-bar__pct {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  font-variant-numeric: tabular-nums;
  width: 40px;
  text-align: right;
}
</style>
