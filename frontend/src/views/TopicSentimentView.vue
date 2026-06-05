<template>
  <div class="topic-sentiment-page">
    <h2 class="page-title">主题与情感交叉分析</h2>

    <!-- 加载状态 -->
    <template v-if="store.loading">
      <LoadingCard :rows="10" />
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

    <!-- 空数据状态 -->
    <el-card v-else-if="!store.data || store.data.cells.length === 0">
      <el-empty description="暂无联合分析数据，请先运行主题建模和情感分析" />
    </el-card>

    <!-- 正常内容 -->
    <template v-else-if="store.data">
      <!-- 热力图 -->
      <el-card>
        <template #header>
          <span>主题×情感 热力图</span>
        </template>
        <TopicSentimentHeatmap
          :data="heatmapData"
        />
      </el-card>

      <!-- 交叉表 -->
      <el-card style="margin-top: 20px">
        <template #header>
          <span>交叉统计表</span>
        </template>
        <el-table :data="crossTableData" stripe border>
          <el-table-column prop="topic_label" label="主题" fixed width="180" />
          <el-table-column
            v-for="cls in store.data.sentiment_classes"
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
import { computed, onMounted } from 'vue'
import { useTopicSentimentStore } from '@/stores/topicSentiment'
import TopicSentimentHeatmap from '@/components/charts/TopicSentimentHeatmap.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'

const store = useTopicSentimentStore()

interface CrossTableRow {
  topic_label: string
  [sentiment: string]: number | string
  total: number
}

/** 热力图数据：优先使用 business_label 作为 Y 轴标签 */
const heatmapData = computed(() => {
  if (!store.data) return { topics: [], sentiment_classes: [], cells: [] }
  const bizLabels = store.data.topic_business_labels || []
  const origLabels = store.data.topics || []
  const displayLabels = bizLabels.length === origLabels.length ? bizLabels : origLabels
  return {
    topics: displayLabels,
    sentiment_classes: store.data.sentiment_classes,
    cells: store.data.cells.flat().map((c, i) => ({
      topic_label: displayLabels[Math.floor(i / (store.data?.sentiment_classes.length || 3))] || c.topic,
      sentiment_class: c.sentiment,
      count: c.count,
    })),
  }
})

const crossTableData = computed<CrossTableRow[]>(() => {
  if (!store.data) return []
  const { topics, topic_business_labels: bizLabels, sentiment_classes: classes, cells } = store.data
  const flatCells = cells.flat()
  const displayLabels = bizLabels && bizLabels.length === topics.length ? bizLabels : topics
  return topics.map((topic, idx) => {
    const displayLabel = displayLabels[idx] || topic
    const row: CrossTableRow = { topic_label: displayLabel, total: 0 }
    for (const cls of classes) {
      const cell = flatCells.find(
        (c) => c.topic === topic && c.sentiment === cls
      )
      const count = cell?.count ?? 0
      row[cls] = count
      row.total += count
    }
    return row
  })
})

function getCellColor(cls: string): string {
  const map: Record<string, string> = {
    positive: '#67c23a',
    neutral: '#909399',
    negative: '#f56c6c',
  }
  return map[cls] || '#303133'
}

onMounted(() => {
  store.fetchMatrix()
})
</script>
