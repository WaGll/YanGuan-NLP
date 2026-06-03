<template>
  <div class="sentiment-page">
    <h2 class="page-title">情感分析</h2>

    <!-- 加载状态 -->
    <template v-if="loading">
      <el-row :gutter="20">
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
      <!-- 情感饼图 -->
      <el-row :gutter="20">
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
              <span>ML模型准确率对比</span>
            </template>
            <SentimentBarChart :data="mlScores" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 分布详情表格 -->
      <el-card style="margin-top: 20px">
        <template #header>
          <span>情感分布统计</span>
        </template>
        <el-table :data="sentimentBins" stripe>
          <el-table-column prop="label" label="情感类别" width="150" />
          <el-table-column prop="count" label="评论数" width="150" />
          <el-table-column prop="percentage" label="占比" min-width="200">
            <template #default="{ row }">
              <el-progress
                :percentage="row.percentage"
                :color="getProgressColor(row.label)"
                :show-text="true"
                :format="() => `${row.percentage}%`"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- ML模型详情表格 -->
      <el-card style="margin-top: 20px" v-if="mlScores.length > 0">
        <template #header>
          <span>ML模型详情</span>
        </template>
        <el-table :data="mlScores" stripe>
          <el-table-column prop="model_name" label="模型名称" />
          <el-table-column prop="cv_mean" label="CV平均准确率">
            <template #default="{ row }">
              {{ `${(row.cv_mean * 100).toFixed(2)}% ± ${(row.cv_std * 100).toFixed(2)}%` }}
            </template>
          </el-table-column>
          <el-table-column prop="best_params" label="最优参数">
            <template #default="{ row }">
              <el-tag
                v-for="(value, key) in row.best_params"
                :key="String(key)"
                size="small"
                style="margin-right: 6px; margin-bottom: 4px"
              >
                {{ key }}: {{ value }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useSentimentStore } from '@/stores/sentiment'
import type { SentimentBin } from '@/api/sentiment'
import SentimentPieChart from '@/components/charts/SentimentPieChart.vue'
import SentimentBarChart from '@/components/charts/SentimentBarChart.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'

const sentimentStore = useSentimentStore()
const { distribution, mlScores, loading, error } = sentimentStore

const sentimentBins = computed<SentimentBin[]>(() => distribution.value?.bins ?? [])

function getProgressColor(label: string): string {
  const map: Record<string, string> = {
    正面: '#67c23a',
    中性: '#909399',
    负面: '#f56c6c',
  }
  return map[label] || '#409eff'
}

onMounted(async () => {
  await sentimentStore.fetchDistribution()
  await sentimentStore.fetchMLScores()
})
</script>
