<template>
  <div class="emote-page">
    <h2 class="page-title">表情分析</h2>

    <!-- 加载状态 -->
    <template v-if="emoteStore.loading">
      <el-row :gutter="24">
        <el-col :span="8" v-for="i in 3" :key="i">
          <LoadingCard />
        </el-col>
      </el-row>
      <el-row :gutter="24" style="margin-top: 20px">
        <el-col :xs="24" :lg="12">
          <LoadingCard :rows="8" />
        </el-col>
        <el-col :xs="24" :lg="12">
          <LoadingCard :rows="8" />
        </el-col>
      </el-row>
    </template>

    <!-- 错误状态 -->
    <el-alert
      v-else-if="emoteStore.error"
      :title="emoteStore.error"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 正常内容 -->
    <template v-else>
      <!-- 统计卡片行 -->
      <el-row :gutter="24">
        <el-col :xs="24" :sm="8">
          <StatCard
            title="表情种类"
            :value="emoteStore.distribution?.total_distinct_emotes ?? 0"
            color="#409EFF"
            icon="ChatDotRound"
          />
        </el-col>
        <el-col :xs="24" :sm="8">
          <StatCard
            title="表情出现总数"
            :value="emoteStore.distribution?.total_emote_occurrences ?? 0"
            color="#67C23A"
            icon="Opportunity"
          />
        </el-col>
        <el-col :xs="24" :sm="8">
          <StatCard
            title="正面表情占比"
            :value="positivePctStr"
            color="#E6A23C"
            icon="TrendCharts"
          />
        </el-col>
      </el-row>

      <!-- 图表行 -->
      <el-row :gutter="24" style="margin-top: 20px">
        <!-- 表情频率柱状图 -->
        <el-col :xs="24" :lg="12">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>表情频率 Top 20</span>
                <el-radio-group v-model="emoteStore.sortBy" size="small" @change="onSortChange">
                  <el-radio-button value="frequency">按频次</el-radio-button>
                  <el-radio-button value="comment_count">按评论数</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div ref="barChartRef" class="chart-container"></div>
          </el-card>
        </el-col>

        <!-- 表情词云 -->
        <el-col :xs="24" :lg="12">
          <el-card>
            <template #header>
              <span>表情词云</span>
            </template>
            <WordCloudChart :data="emoteStore.wordcloudData" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 情感相关性表格 -->
      <el-card style="margin-top: 20px">
        <template #header>
          <span>表情-文本情感相关性</span>
        </template>
        <el-table :data="emoteStore.correlations" stripe max-height="500">
          <el-table-column prop="emote_name" label="表情名称" width="140" />
          <el-table-column prop="emote_sentiment" label="表情情感" width="100">
            <template #default="{ row }">
              <el-tag :type="sentimentTagType(row.emote_sentiment)" size="small" effect="plain">
                {{ sentimentLabel(row.emote_sentiment) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="avg_text_sentiment" label="文本平均情感分" width="140">
            <template #default="{ row }">
              {{ row.avg_text_sentiment.toFixed(4) }}
            </template>
          </el-table-column>
          <el-table-column prop="sentiment_delta" label="情感偏差" width="120">
            <template #default="{ row }">
              <span :style="{ color: row.sentiment_delta >= 0 ? '#67C23A' : '#F56C6C' }">
                {{ row.sentiment_delta >= 0 ? '+' : '' }}{{ row.sentiment_delta.toFixed(4) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="comment_count" label="评论数" width="100" />
          <el-table-column label="解读" min-width="200">
            <template #default="{ row }">
              {{ interpretDelta(row) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useEmotesStore } from '@/stores/emotes'
import StatCard from '@/components/common/StatCard.vue'
import WordCloudChart from '@/components/charts/WordCloudChart.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'

const emoteStore = useEmotesStore()

// --- 统计 ---
const positivePctStr = computed(() => {
  const bd = emoteStore.distribution?.sentiment_breakdown
  if (!bd) return '0%'
  return `${bd.positive_pct}%`
})

// --- 柱状图 ---
const barChartRef = ref<HTMLElement | null>(null)
let barChart: echarts.ECharts | null = null

function sentimentColor(sentiment: string): string {
  if (sentiment === 'positive') return '#67C23A'
  if (sentiment === 'negative') return '#F56C6C'
  return '#909399'
}

function renderBarChart() {
  if (!barChartRef.value) return
  if (!barChart) {
    barChart = echarts.init(barChartRef.value)
  }

  const items = emoteStore.emotes.slice(0, 20)
  const names = items.map((e) => `[${e.name}]`).reverse()
  const values = items.map((e) => e.frequency).reverse()
  const colors = items.map((e) => sentimentColor(e.sentiment)).reverse()

  barChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `${p.name}<br/>频次: ${p.value}`
      },
    },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', name: '出现次数' },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
        barMaxWidth: 24,
      },
    ],
  })
}

function onSortChange() {
  emoteStore.fetchDistribution()
}

watch(
  () => emoteStore.emotes,
  () => nextTick(() => renderBarChart()),
  { deep: true }
)

// --- 工具函数 ---
function sentimentTagType(s: string): 'success' | 'danger' | 'info' {
  if (s === 'positive') return 'success'
  if (s === 'negative') return 'danger'
  return 'info'
}

function sentimentLabel(s: string): string {
  if (s === 'positive') return '正面'
  if (s === 'negative') return '负面'
  return '中性'
}

function interpretDelta(row: { emote_sentiment: string; sentiment_delta: number }): string {
  const d = row.sentiment_delta
  const emote = row.emote_sentiment
  if (Math.abs(d) < 0.05) return '表情情感与文本情感基本一致'
  if (emote === 'positive' && d < 0) return '文本比表情更负面，可能表情用于缓解语气'
  if (emote === 'negative' && d > 0) return '文本比表情更正面，可能表情表示轻度不满'
  if (emote === 'neutral' && d > 0.1) return '中性表情出现在偏正面文本中'
  if (emote === 'neutral' && d < -0.1) return '中性表情出现在偏负面文本中'
  return '表情情感与文本情感方向一致'
}

// --- resize ---
function handleResize() {
  barChart?.resize()
}

onMounted(async () => {
  await Promise.all([
    emoteStore.fetchDistribution(),
    emoteStore.fetchCorrelations(),
    emoteStore.fetchWordcloud(),
  ])
  nextTick(() => renderBarChart())
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  barChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.emote-page {
  padding: 0;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--el-text-color-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 400px;
}
</style>
