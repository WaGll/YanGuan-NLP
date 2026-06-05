<template>
  <div class="trends-page">
    <h2 class="page-title">趋势分析</h2>

    <!-- 筛选区域 -->
    <el-card style="margin-bottom: 20px">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">趋势类型：</span>
          <el-select v-model="store.seriesType" placeholder="选择趋势类型" @change="store.fetchTrends()">
            <el-option label="情感趋势" value="sentiment" />
            <el-option label="关键词趋势" value="keyword" />
            <el-option label="主题趋势" value="topic" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">时间粒度：</span>
          <el-select v-model="store.granularity" placeholder="时间粒度" @change="store.fetchTrends()">
            <el-option label="按日" value="day" />
            <el-option label="按周" value="week" />
            <el-option label="按月" value="month" />
            <el-option label="按年" value="year" />
          </el-select>
        </div>
      </div>
    </el-card>

    <!-- 加载状态 -->
    <template v-if="store.loading">
      <LoadingCard :rows="8" />
    </template>

    <!-- 错误状态 -->
    <el-alert
      v-else-if="store.error"
      :title="store.error"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 空数据 -->
    <el-empty
      v-else-if="!store.data || store.data.buckets.length === 0"
      description="暂无趋势数据"
    />

    <!-- 趋势图表 -->
    <template v-else-if="store.data">
      <el-card style="margin-bottom: 20px">
        <TrendLineChart
          :data="trendChartData"
          :title="`${seriesTypeLabel}趋势 (${granularityLabel})`"
        />
      </el-card>

      <!-- 统计摘要 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :xs="24" :sm="8">
          <StatCard
            title="数据点数"
            :value="store.data.total_points"
            icon="TrendCharts"
            color="#409eff"
          />
        </el-col>
        <el-col :xs="24" :sm="8">
          <StatCard
            title="平均情感得分"
            :value="avgSentimentStr"
            icon="DataLine"
            color="#e6a23c"
          />
        </el-col>
        <el-col :xs="24" :sm="8">
          <StatCard
            title="总评论数"
            :value="totalCommentCount"
            icon="ChatDotSquare"
            color="#67c23a"
          />
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useTrendsStore } from '@/stores/trends'
import TrendLineChart from '@/components/charts/TrendLineChart.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'
import StatCard from '@/components/common/StatCard.vue'

const store = useTrendsStore()

const seriesTypeLabel = computed(() => {
  const map: Record<string, string> = {
    sentiment: '情感',
    keyword: '关键词',
    topic: '主题',
  }
  return map[store.seriesType] || store.seriesType
})

const granularityLabel = computed(() => {
  const map: Record<string, string> = {
    day: '按日',
    week: '按周',
    month: '按月',
    year: '按年',
  }
  return map[store.granularity] || store.granularity
})

const trendChartData = computed(() => {
  if (!store.data) return []
  return store.data.buckets.map((b) => ({
    bucket_start: b.bucket_start,
    value: b.avg_sentiment ?? 0,
    comment_count: b.comment_count,
  }))
})

const avgSentiment = computed(() => {
  if (!store.data || store.data.buckets.length === 0) return null
  const buckets = store.data.buckets.filter((b) => b.avg_sentiment !== null)
  if (buckets.length === 0) return null
  return buckets.reduce((s, b) => s + (b.avg_sentiment ?? 0), 0) / buckets.length
})

const avgSentimentStr = computed(() => {
  return avgSentiment.value?.toFixed(3) ?? '--'
})

const totalCommentCount = computed(() => {
  if (!store.data) return 0
  return store.data.buckets.reduce((s, b) => s + b.comment_count, 0)
})

onMounted(() => {
  store.fetchTrends()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}
</style>
