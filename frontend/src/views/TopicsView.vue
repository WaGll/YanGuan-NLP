<template>
  <div class="topics-page">
    <h2 class="page-title">主题分析</h2>

    <!-- 模型选择 -->
    <el-card style="margin-bottom: 20px">
      <div class="model-selector">
        <span class="model-selector__label">主题模型：</span>
        <el-radio-group v-model="selectedModel">
          <el-radio-button value="lda">LDA</el-radio-button>
          <el-radio-button value="bertopic" :disabled="true">BERTopic（已停用）</el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

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

    <!-- 主题表格 -->
    <template v-else>
      <el-card>
        <template #header>
          <span>主题列表（{{ topics.length }}个主题）</span>
        </template>
        <el-table :data="topics" stripe @row-click="handleRowClick" style="cursor: pointer">
          <el-table-column prop="topic_index" label="编号" width="80" />
          <el-table-column prop="label" label="主题标签" width="180" />
          <el-table-column label="核心词" min-width="300">
            <template #default="{ row }">
              <el-tag
                v-for="(word, idx) in row.top_words"
                :key="idx"
                size="small"
                :type="getTagType(idx)"
                style="margin-right: 6px; margin-bottom: 4px"
              >
                {{ word }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="coherence_score" label="一致性得分" width="140">
            <template #default="{ row }">
              <el-progress
                :percentage="Math.round((row.coherence_score || 0) * 100)"
                :color="getCoherenceColor(row.coherence_score)"
                :show-text="true"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 主题详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="`主题详情：${selectedTopic?.label || '--'}`"
      width="600px"
    >
      <template v-if="selectedTopic">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="主题编号">
            {{ selectedTopic.topic_index }}
          </el-descriptions-item>
          <el-descriptions-item label="主题标签">
            {{ selectedTopic.label }}
          </el-descriptions-item>
          <el-descriptions-item label="一致性得分">
            {{ selectedTopic.coherence_score?.toFixed(4) ?? '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="核心词">
            <el-tag
              v-for="(word, idx) in selectedTopic.top_words"
              :key="idx"
              size="small"
              style="margin-right: 6px; margin-bottom: 4px"
            >
              {{ word }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import client from '@/api/client'
import LoadingCard from '@/components/common/LoadingCard.vue'

interface Topic {
  topic_index: number
  label: string
  top_words: string[]
  coherence_score: number
}

const selectedModel = ref('lda')
const topics = ref<Topic[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const dialogVisible = ref(false)
const selectedTopic = ref<Topic | null>(null)

function getTagType(index: number): '' | 'success' | 'warning' | 'info' | 'danger' {
  const types: Array<'' | 'success' | 'warning' | 'info' | 'danger'> = [
    'success', 'warning', 'info', 'danger', '',
  ]
  return types[index % types.length]
}

function getCoherenceColor(score: number | undefined): string {
  if (!score) return '#909399'
  if (score > 0.6) return '#67c23a'
  if (score > 0.4) return '#e6a23c'
  return '#f56c6c'
}

function handleRowClick(row: Topic) {
  selectedTopic.value = row
  dialogVisible.value = true
}

async function fetchTopics() {
  loading.value = true
  error.value = null
  try {
    const res = await client.get('/topics', {
      params: { model: selectedModel.value },
    })
    topics.value = res.data
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '获取主题数据失败'
    error.value = msg
    console.error('Topics fetch error:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTopics()
})
</script>

<style scoped>
.model-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-selector__label {
  font-size: 14px;
  color: var(--text-regular);
}
</style>
