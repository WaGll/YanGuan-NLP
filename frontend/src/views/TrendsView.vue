<template>
  <div class="trends-page">
    <h2 class="page-title">趋势分析</h2>

    <!-- 筛选区域 -->
    <el-card style="margin-bottom: 20px">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">趋势类型：</span>
          <el-select v-model="trendType" placeholder="选择趋势类型" @change="fetchTrends">
            <el-option label="情感趋势" value="sentiment" />
            <el-option label="关键词趋势" value="keyword" />
            <el-option label="主题趋势" value="topic" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">日期范围：</span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="fetchTrends"
          />
        </div>
      </div>
    </el-card>

    <!-- 加载状态 -->
    <template v-if="loading">
      <LoadingCard :rows="8" />
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

    <!-- 趋势图表 -->
    <template v-else>
      <div v-if="trendSeriesList.length === 0" class="empty-state">
        <el-empty description="暂无趋势数据" />
      </div>
      <div v-else>
        <el-card
          v-for="(series, index) in trendSeriesList"
          :key="index"
          style="margin-bottom: 20px"
        >
          <TrendLineChart
            :data="series.data"
            :title="series.title"
          />
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import client from '@/api/client'
import type { TrendDataItem } from '@/components/charts/TrendLineChart.vue'
import TrendLineChart from '@/components/charts/TrendLineChart.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'

interface TrendSeries {
  title: string
  data: TrendDataItem[]
}

const trendType = ref('sentiment')
const dateRange = ref<[string, string] | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const trendSeriesList = ref<TrendSeries[]>([])

async function fetchTrends() {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, unknown> = {
      type: trendType.value,
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await client.get('/trends', { params })
    const raw = res.data as TrendSeries[]
    trendSeriesList.value = raw
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '获取趋势数据失败'
    error.value = msg
    console.error('Trends fetch error:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTrends()
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
  color: var(--text-regular);
  white-space: nowrap;
}

.empty-state {
  padding: 60px 0;
}
</style>
