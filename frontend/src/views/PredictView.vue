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
    <!-- ════════════════════════════════════════════════════════ -->
    <!-- GB 梯度提升模型预测 -->
    <!-- ════════════════════════════════════════════════════════ -->
    <div style="margin-top: 32px">
      <h2 class="page-title" style="font-size: 18px; margin-bottom: 16px">GB Model Prediction</h2>

      <!-- GB single input -->
      <el-card>
        <template #header>
          <div class="history-header">
            <span>GB Single Prediction</span>
            <el-select
              v-model="gbModel"
              size="small"
              style="width: 130px"
              placeholder="Model"
            >
              <el-option label="Best" value="best" />
              <el-option label="XGBoost" value="xgboost" />
              <el-option label="LightGBM" value="lightgbm" />
              <el-option label="CatBoost" value="catboost" />
            </el-select>
          </div>
        </template>
        <el-input
          v-model="gbInputText"
          type="textarea"
          :rows="3"
          placeholder="Enter comment text for GB prediction..."
          maxlength="500"
          show-word-limit
        />
        <div class="predict-actions">
          <el-button
            type="primary"
            :loading="gbPredicting"
            :disabled="!gbInputText.trim()"
            @click="handleGBPredict"
          >
            Predict
          </el-button>
          <el-button
            type="warning"
            :loading="gbTraining"
            @click="handleGBTrain"
          >
            Train Models
          </el-button>
          <el-button @click="gbInputText = ''; gbResult = null" :disabled="!gbInputText">
            Clear
          </el-button>
        </div>
      </el-card>

      <!-- GB batch input -->
      <el-card style="margin-top: 16px">
        <template #header>
          <span>Batch Input (one comment per line)</span>
        </template>
        <el-input
          v-model="gbBatchText"
          type="textarea"
          :rows="5"
          placeholder="Put one comment per line..."
        />
        <div class="predict-actions">
          <el-button
            type="primary"
            :loading="gbBatchPredicting"
            :disabled="!gbBatchText.trim()"
            @click="handleGBBatchPredict"
          >
            Batch Predict
          </el-button>
          <el-button @click="gbBatchText = ''; gbBatchResults = []" :disabled="!gbBatchText">
            Clear
          </el-button>
        </div>
      </el-card>

      <!-- GB single result -->
      <el-card v-if="gbResult" style="margin-top: 16px">
        <template #header>
          <span>GB Prediction Result</span>
        </template>
        <div class="result-row">
          <div class="result-item">
            <span class="result-label">Sentiment:</span>
            <el-tag :type="getSentimentTagType(gbResult.sentiment_class)" size="large" effect="dark">
              {{ getSentimentLabel(gbResult.sentiment_class) }}
            </el-tag>
          </div>
          <div class="result-item">
            <span class="result-label">Model:</span>
            <el-tag size="small" type="info">{{ gbResult.model_used }}</el-tag>
          </div>
        </div>
        <div class="result-item" style="margin-top: 12px">
          <span class="result-label">Probabilities:</span>
          <span
            v-for="(prob, cls) in gbResult.probabilities"
            :key="cls"
            style="margin-right: 12px; font-size: 13px; color: #1e293b"
          >
            <strong>{{ cls }}</strong>: {{ (prob * 100).toFixed(1) }}%
          </span>
        </div>
      </el-card>

      <!-- GB batch results -->
      <el-card v-if="gbBatchResults.length > 0" style="margin-top: 16px">
        <template #header>
          <span>Batch Results ({{ gbBatchResults.length }} items)</span>
        </template>
        <el-table :data="gbBatchResults" stripe max-height="300">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="text" label="Text" min-width="200" show-overflow-tooltip />
          <el-table-column label="Sentiment" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getSentimentTagType(row.sentiment_class)" size="small" effect="dark">
                {{ getSentimentLabel(row.sentiment_class) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- GB model list -->
      <el-card style="margin-top: 16px">
        <template #header>
          <div class="history-header">
            <span>Available Models</span>
            <el-button size="small" @click="loadGBModels" :loading="gbModelsLoading">
              Refresh
            </el-button>
          </div>
        </template>
        <div v-if="gbModelList.models.length === 0 && !gbModelsLoading" style="color: #909399; font-size: 13px">
          No trained models found. Click "Train Models" to train.
        </div>
        <el-table v-else :data="gbModelList.models" size="small">
          <el-table-column prop="name" label="Model" />
          <el-table-column label="Best" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_best" type="success" size="small">Best</el-tag>
              <span v-else style="color: #94a3b8">--</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { predictComment, type PredictResult } from '@/api/predict'
import {
  predictGB,
  predictGBBatch,
  trainGB,
  listGBModels,
} from '@/api/predict'
import type {
  GBPredictResult,
  GBBatchPredictItem,
  GBModelList,
} from '@/types/predict'

interface HistoryItem {
  text: string
  result: PredictResult
}

const inputText = ref('')
const predicting = ref(false)
const currentResult = ref<PredictResult | null>(null)
const predictionHistory = ref<HistoryItem[]>([])

// ── GB Model state ──
const gbModel = ref('best')
const gbInputText = ref('')
const gbBatchText = ref('')
const gbPredicting = ref(false)
const gbBatchPredicting = ref(false)
const gbTraining = ref(false)
const gbResult = ref<GBPredictResult | null>(null)
const gbBatchResults = ref<GBBatchPredictItem[]>([])
const gbModelList = ref<GBModelList>({ models: [], has_trained: false })
const gbModelsLoading = ref(false)

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

// ── GB handlers ──

async function handleGBPredict() {
  if (!gbInputText.value.trim()) return
  gbPredicting.value = true
  gbResult.value = null
  try {
    gbResult.value = await predictGB(gbInputText.value.trim(), gbModel.value)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'GB predict failed'
    console.error('GB predict error:', err)
    alert('Prediction failed: ' + msg)
  } finally {
    gbPredicting.value = false
  }
}

async function handleGBBatchPredict() {
  const lines = gbBatchText.value.split('\n').map((l) => l.trim()).filter(Boolean)
  if (lines.length === 0) return
  gbBatchPredicting.value = true
  try {
    const res = await predictGBBatch(lines, gbModel.value)
    gbBatchResults.value = res.items
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'GB batch predict failed'
    console.error('GB batch predict error:', err)
    alert('Batch prediction failed: ' + msg)
  } finally {
    gbBatchPredicting.value = false
  }
}

async function handleGBTrain() {
  gbTraining.value = true
  try {
    const result = await trainGB()
    const count = result.models ? Object.keys(result.models).length : 0
    alert('Training complete: ' + count + ' models trained.')
    await loadGBModels()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Training failed'
    console.error('GB train error:', err)
    alert('Training failed: ' + msg)
  } finally {
    gbTraining.value = false
  }
}

async function loadGBModels() {
  gbModelsLoading.value = true
  try {
    gbModelList.value = await listGBModels()
  } catch (err: unknown) {
    console.error('List GB models error:', err)
  } finally {
    gbModelsLoading.value = false
  }
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
