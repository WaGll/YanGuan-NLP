<template>
  <div class="topics-page">
    <h2 class="page-title">主题分析</h2>

    <!-- 复合筛选条 -->
    <div class="filter-bar">
      <div class="filter-bar__left">
        <span class="filter-label">主题模型</span>
        <el-radio-group v-model="store.method" size="small" @change="store.fetchTopics()">
          <el-radio-button value="lda">LDA</el-radio-button>
          <el-radio-button value="bertopic">BERTopic</el-radio-button>
        </el-radio-group>
      </div>
      <span class="filter-hint" @click="showTopicInfo">↗</span>
    </div>

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
    <el-card v-else-if="store.topics.length === 0">
      <el-empty description="暂无主题数据，请先运行数据分析管道" />
    </el-card>

    <!-- 主题表格 -->
    <template v-else>
      <el-card>
        <template #header>
          <span>主题列表（{{ store.topics.length }}个主题）</span>
        </template>
        <el-table :data="store.topics" stripe @row-click="handleRowClick" style="cursor: pointer">
          <el-table-column prop="topic_index" label="编号" width="80" />
          <el-table-column label="主题标签" width="200">
            <template #default="{ row }">
              <div class="topic-label-cell">
                <span class="business-label">{{ row.business_label || row.label || `主题 ${row.topic_index + 1}` }}</span>
                <span v-if="row.business_label && row.label" class="keyword-label">{{ row.label }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="核心词" min-width="300">
            <template #default="{ row }">
              <el-tag
                v-for="(kw, idx) in (row.keywords || []).slice(0, 8)"
                :key="idx"
                size="small"
                :style="getTagStyle(idx, kw.rank)"
                style="margin-right: 6px; margin-bottom: 4px"
              >
                {{ kw.word }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="doc_count" label="文档数" width="100" />
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
      :title="`主题详情：${selectedTopicLabel}`"
      width="700px"
    >
      <template v-if="store.selectedTopic">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="主题编号">
            {{ store.selectedTopic.topic.topic_index }}
          </el-descriptions-item>
          <el-descriptions-item label="业务标签">
            <strong>{{ store.selectedTopic.topic.business_label || '--' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="关键词标签">
            {{ store.selectedTopic.topic.label || `主题 ${store.selectedTopic.topic.topic_index + 1}` }}
          </el-descriptions-item>
          <el-descriptions-item label="一致性得分">
            {{ store.selectedTopic.topic.coherence_score?.toFixed(4) ?? '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="全部关键词">
            <el-tag
              v-for="(kw, idx) in store.selectedTopic.topic.keywords"
              :key="idx"
              size="small"
              :style="getTagStyle(idx, kw.rank)"
              style="margin-right: 6px; margin-bottom: 4px"
            >
              {{ kw.word }} ({{ kw.weight.toFixed(3) }})
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="代表性评论">
            <div
              v-for="(comment, idx) in store.selectedTopic.representative_comments.slice(0, 5)"
              :key="idx"
              style="margin-bottom: 8px; padding: 8px; background: var(--el-fill-color-light); border-radius: 4px; font-size: 13px;"
            >
              {{ comment }}
            </div>
            <span v-if="store.selectedTopic.representative_comments.length === 0" style="color: #909399">
              暂无代表性评论
            </span>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTopicsStore } from '@/stores/topics'
import type { TopicItem } from '@/types/topics'
import LoadingCard from '@/components/common/LoadingCard.vue'

const store = useTopicsStore()

const dialogVisible = ref(false)

const selectedTopicLabel = computed(() => {
  if (!store.selectedTopic) return '--'
  return store.selectedTopic.topic.business_label || store.selectedTopic.topic.label || `主题 ${store.selectedTopic.topic.topic_index + 1}`
})

function getTagStyle(_index: number, rank: number): Record<string, string> {
  // 首词（rank=1）使用薄荷绿点缀，其余统一极简灰底
  if (rank === 1) {
    return { background: '#E8F9F1', color: '#006D44', border: 'none' }
  }
  return { background: '#F5F5F5', color: '#4A5551', border: 'none' }
}

function getCoherenceColor(score: number | undefined): string {
  if (!score) return '#B0B8B5'
  if (score > 0.6) return '#006D44'
  if (score > 0.4) return '#3DA775'
  return '#A6E7C9'
}

function showTopicInfo() {
  // 轻提示：主题模型说明
}

function handleRowClick(row: TopicItem) {
  dialogVisible.value = true
  store.fetchTopicDetail(row)
}

onMounted(() => {
  store.fetchTopics()
})
</script>

<style scoped>
/* ── 主题标签单元格 ── */
.topic-label-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.business-label {
  font-weight: 600;
  font-size: 14px;
  color: #2d3748;
}

.keyword-label {
  font-size: 11px;
  color: #a0aec0;
}

/* ── 复合筛选条 ── */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 20px 0;
}

.filter-bar__left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #4A5551;
}

.filter-hint {
  font-size: 16px;
  color: #B0B8B5;
  cursor: pointer;
  transition: color 0.2s;
}

.filter-hint:hover {
  color: #006D44;
}
</style>
