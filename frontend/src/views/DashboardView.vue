<template>
  <div class="dashboard-page">
    <h2 class="page-title">仪表盘</h2>

    <!-- 加载状态 -->
    <template v-if="loading">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :lg="6" v-for="n in 4" :key="n">
          <LoadingCard :rows="3" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :xs="24" :lg="12">
          <LoadingCard :rows="6" />
        </el-col>
        <el-col :xs="24" :lg="12">
          <LoadingCard :rows="8" />
        </el-col>
      </el-row>
    </template>

    <!-- 错误状态 -->
    <el-alert
      v-else-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 正常内容 -->
    <template v-else>
      <!-- 统计卡片行 -->
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :lg="6">
          <StatCard
            title="总评论数"
            :value="stats?.total_comments ?? 0"
            icon="ChatLineSquare"
            color="#409eff"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :lg="6">
          <StatCard
            title="独立用户"
            :value="stats?.unique_users ?? 0"
            icon="User"
            color="#67c23a"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :lg="6">
          <StatCard
            title="平均情感"
            :value="formatAvgSentiment(stats?.avg_sentiment)"
            icon="TrendCharts"
            color="#e6a23c"
          />
        </el-col>
        <el-col :xs="24" :sm="12" :lg="6">
          <StatCard
            title="数据时间范围"
            :value="formatDateRange(stats?.date_range_start, stats?.date_range_end)"
            icon="Calendar"
            color="#909399"
          />
        </el-col>
      </el-row>

      <!-- 图表行 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :xs="24" :lg="12">
          <el-card>
            <template #header>
              <span>情感分布</span>
            </template>
            <SentimentPieChart :data="sentimentBins" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="12">
          <el-card>
            <template #header>
              <span>高频关键词 TOP 20</span>
            </template>
            <KeywordBarChart :data="keywordItems" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { fetchSentiment } from '@/api/sentiment'
import { fetchKeywords } from '@/api/keywords'
import type { SentimentBin } from '@/api/sentiment'
import type { KeywordItem } from '@/api/keywords'
import StatCard from '@/components/common/StatCard.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'
import SentimentPieChart from '@/components/charts/SentimentPieChart.vue'
import KeywordBarChart from '@/components/charts/KeywordBarChart.vue'

const dashboardStore = useDashboardStore()
const { stats, loading, error } = dashboardStore

const sentimentBins = ref<SentimentBin[]>([])
const keywordItems = ref<KeywordItem[]>([])

function formatAvgSentiment(val: number | undefined): string {
  if (val === undefined || val === null) return '--'
  return val.toFixed(3)
}

function formatDateRange(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) return '--'
  return `${start.slice(0, 10)} ~ ${end.slice(0, 10)}`
}

onMounted(async () => {
  await dashboardStore.fetchStats()

  try {
    const sentimentRes = await fetchSentiment()
    sentimentBins.value = sentimentRes.bins
  } catch {
    sentimentBins.value = [
      { label: '正面', count: 0, percentage: 0 },
      { label: '中性', count: 0, percentage: 0 },
      { label: '负面', count: 0, percentage: 0 },
    ]
  }

  try {
    keywordItems.value = await fetchKeywords('frequency', 20)
  } catch {
    keywordItems.value = []
  }
})
</script>
