<template>
  <div class="topic-sentiment-page">
    <h2 class="page-title">主题与情感交叉分析</h2>

    <!-- 加载状态 -->
    <template v-if="loading">
      <LoadingCard :rows="10" />
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
      <!-- 热力图 -->
      <el-card>
        <template #header>
          <span>主题×情感 热力图</span>
        </template>
        <TopicSentimentHeatmap :data="heatmapData" />
      </el-card>

      <!-- 交叉表 -->
      <el-card style="margin-top: 20px">
        <template #header>
          <span>交叉统计表</span>
        </template>
        <el-table :data="crossTableData" stripe border>
          <el-table-column prop="topic_label" label="主题" fixed width="180" />
          <el-table-column
            v-for="cls in sentimentClasses"
            :key="cls"
            :prop="cls"
            :label="cls"
            align="center"
            width="120"
          >
            <template #default="{ row }">
              <span :style="{ color: getCellColor(cls), fontWeight: '600' }">
                {{ row[cls] ?? 0 }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="total" label="合计" align="center" width="100">
            <template #default="{ row }">
              <strong>{{ row.total }}</strong>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import client from '@/api/client'
import type { HeatmapData, HeatmapCell } from '@/components/charts/TopicSentimentHeatmap.vue'
import TopicSentimentHeatmap from '@/components/charts/TopicSentimentHeatmap.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'

interface CrossTableRow {
  topic_label: string
  [sentiment: string]: number | string
  total: number
}

const loading = ref(false)
const error = ref<string | null>(null)
const heatmapData = ref<HeatmapData>({
  topics: [],
  sentiment_classes: [],
  cells: [],
})
const sentimentClasses = ref<string[]>([])
const crossTableData = ref<CrossTableRow[]>([])

function getCellColor(cls: string): string {
  const map: Record<string, string> = {
    正面: '#67c23a',
    中性: '#909399',
    负面: '#f56c6c',
  }
  return map[cls] || '#303133'
}

function buildCrossTable(
  topics: string[],
  classes: string[],
  cells: HeatmapCell[]
): CrossTableRow[] {
  return topics.map((topic) => {
    const row: CrossTableRow = { topic_label: topic, total: 0 }
    for (const cls of classes) {
      const cell = cells.find((c) => c.topic_label === topic && c.sentiment_class === cls)
      const count = cell?.count ?? 0
      row[cls] = count
      row.total += count
    }
    return row
  })
}

async function fetchTopicSentiment() {
  loading.value = true
  error.value = null
  try {
    const res = await client.get('/topic-sentiment')
    const raw = res.data as {
      topics: string[]
      sentiment_classes: string[]
      cells: HeatmapCell[]
    }
    heatmapData.value = raw
    sentimentClasses.value = raw.sentiment_classes
    crossTableData.value = buildCrossTable(raw.topics, raw.sentiment_classes, raw.cells)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '获取主题×情感数据失败'
    error.value = msg
    console.error('Topic-sentiment fetch error:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTopicSentiment()
})
</script>
