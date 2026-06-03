<template>
  <div class="predict-page">
    <h2 class="page-title">实时预测</h2>

    <!-- 输入区域 -->
    <el-card>
      <template #header>
        <span>输入评论文本</span>
      </template>
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="4"
        placeholder="请输入评论文本，点击按钮进行情感预测..."
        maxlength="500"
        show-word-limit
      />
      <div class="predict-actions">
        <el-button
          type="primary"
          :loading="predicting"
          :disabled="!inputText.trim()"
          @click="handlePredict"
        >
          预测
        </el-button>
        <el-button @click="clearInput" :disabled="!inputText">清空</el-button>
      </div>
    </el-card>

    <!-- 预测结果 -->
    <el-card v-if="currentResult" style="margin-top: 20px">
      <template #header>
        <span>预测结果</span>
      </template>
      <div class="result-row">
        <div class="result-item">
          <span class="result-label">情感类别：</span>
          <el-tag
            :type="getSentimentTagType(currentResult.sentiment_class)"
            size="large"
            effect="dark"
          >
            {{ getSentimentLabel(currentResult.sentiment_class) }}
          </el-tag>
        </div>
        <div class="result-item">
          <span class="result-label">SnowNLP得分：</span>
          <span class="result-value">{{ currentResult.snownlp_score?.toFixed(4) }}</span>
        </div>
      </div>
      <div class="result-item" style="margin-top: 12px">
        <span class="result-label">关键词：</span>
        <el-tag
          v-for="(word, idx) in currentResult.top_keywords"
          :key="idx"
          size="small"
          :type="getKeywordTagType(idx)"
          style="margin-right: 6px; margin-bottom: 4px"
        >
          {{ word }}
        </el-tag>
        <span v-if="!currentResult.top_keywords?.length" style="color: #909399">无</span>
      </div>
    </el-card>

    <!-- 预测历史 -->
    <el-card v-if="predictionHistory.length > 0" style="margin-top: 20px">
      <template #header>
        <div class="history-header">
          <span>历史预测（{{ predictionHistory.length }}条）</span>
          <el-button size="small" type="danger" text @click="predictionHistory = []">
            清空历史
          </el-button>
        </div>
      </template>
      <el-table :data="predictionHistory" stripe max-height="400">
        <el-table-column prop="text" label="评论文本" min-width="200" show-overflow-tooltip />
        <el-table-column label="情感类别" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="getSentimentTagType(row.result.sentiment_class)"
              size="small"
              effect="dark"
            >
              {{ getSentimentLabel(row.result.sentiment_class) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="SnowNLP得分" width="120" align="center">
          <template #default="{ row }">
            {{ row.result.snownlp_score?.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column label="关键词" min-width="180">
          <template #default="{ row }">
            <el-tag
              v-for="(word, idx) in row.result.top_keywords"
              :key="idx"
              size="small"
              style="margin-right: 4px"
            >
              {{ word }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { predictComment, type PredictResult } from '@/api/predict'

interface HistoryItem {
  text: string
  result: PredictResult
}

const inputText = ref('')
const predicting = ref(false)
const currentResult = ref<PredictResult | null>(null)
const predictionHistory = ref<HistoryItem[]>([])

function getSentimentLabel(cls: string): string {
  const map: Record<string, string> = {
    positive: '正面',
    negative: '负面',
    neutral: '中性',
  }
  return map[cls] || cls
}

function getSentimentTagType(cls: string): 'success' | 'danger' | 'info' | 'warning' | '' {
  const map: Record<string, 'success' | 'danger' | 'info' | 'warning' | ''> = {
    positive: 'success',
    negative: 'danger',
    neutral: 'info',
  }
  return map[cls] || 'info'
}

function getKeywordTagType(index: number): '' | 'success' | 'warning' | 'info' | 'danger' {
  const types: Array<'' | 'success' | 'warning' | 'info' | 'danger'> = [
    'success', 'warning', 'info', 'danger', '',
  ]
  return types[index % types.length]
}

function clearInput() {
  inputText.value = ''
  currentResult.value = null
}

async function handlePredict() {
  if (!inputText.value.trim()) return

  predicting.value = true
  currentResult.value = null

  try {
    const result = await predictComment(inputText.value.trim())
    currentResult.value = result
    predictionHistory.value.unshift({
      text: inputText.value.trim(),
      result,
    })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '预测失败'
    console.error('Predict error:', err)
    alert(`预测失败：${msg}`)
  } finally {
    predicting.value = false
  }
}
</script>

<style scoped>
.predict-actions {
  margin-top: 12px;
  display: flex;
  gap: 12px;
}

.result-row {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.result-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.result-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
