<template>
  <el-dialog
    v-model="visible"
    title="Search"
    width="520px"
    :show-close="true"
    :close-on-click-modal="true"
    class="search-dialog"
    :append-to-body="true"
  >
    <el-input
      v-model="query"
      ref="searchInputRef"
      placeholder="Search pages..."
      :prefix-icon="Search"
      size="large"
      clearable
      @keydown.enter="navigateToFirst"
    />
    <div class="search-results" v-if="filteredResults.length > 0">
      <div
        v-for="item in filteredResults"
        :key="item.path"
        class="search-result-item"
        :class="{ 'search-result-item--active': activeIndex === item.index }"
        @click="navigateTo(item)"
        @mouseenter="activeIndex = item.index"
      >
        <span class="search-result-name">{{ item.label }}</span>
        <span class="search-result-path">{{ item.path }}</span>
      </div>
    </div>
    <div v-else-if="query" class="search-empty">
      No results found
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

const router = useRouter()
const visible = ref(false)
const query = ref('')
const activeIndex = ref(0)
const searchInputRef = ref<any>(null)

const searchItems = [
  { path: '/dashboard', label: 'Dashboard', keywords: ['overview', '仪表盘', 'kpi', 'stats'] },
  { path: '/topics', label: 'Topics', keywords: ['topic', '主题', 'bertopic', 'lda', 'model'] },
  { path: '/sentiment', label: 'Sentiment', keywords: ['sentiment', '情感', 'emotion', 'distribution'] },
  { path: '/trends', label: 'Trends', keywords: ['trend', '趋势', 'time', 'timeline'] },
  { path: '/network', label: 'Network', keywords: ['network', '网络', 'graph', 'cooccurrence', 'metrics'] },
  { path: '/predict', label: 'Forecast', keywords: ['predict', '预测', 'forecast', 'gb', 'xgboost'] },
  { path: '/topic-sentiment', label: 'Topic×Sentiment', keywords: ['topic sentiment', '主题情感', 'heatmap'] },
  { path: '/network-analytics', label: 'Network Analytics', keywords: ['analytics', 'metrics', '分析', 'centrality'] },
  { path: '/emotes', label: 'Emotes', keywords: ['emote', '表情', 'emoji', 'reaction'] },
]

const filteredResults = computed(() => {
  if (!query.value.trim()) return []
  const q = query.value.toLowerCase()
  return searchItems
    .map((item, idx) => ({ ...item, index: idx }))
    .filter((item) =>
      item.label.toLowerCase().includes(q) ||
      item.path.toLowerCase().includes(q) ||
      item.keywords.some((k) => k.toLowerCase().includes(q))
    )
})

function navigateTo(item: { path: string }) {
  router.push(item.path)
  visible.value = false
}

function navigateToFirst() {
  if (filteredResults.value.length > 0) {
    navigateTo(filteredResults.value[0])
  }
}

function open() {
  query.value = ''
  activeIndex.value = 0
  visible.value = true
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    open()
  }
}

watch(visible, (val) => {
  if (!val) {
    query.value = ''
    activeIndex.value = 0
  }
})

onMounted(() => {
  window.addEventListener('open-search', open)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('open-search', open)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.search-results {
  margin-top: 16px;
  max-height: 320px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
}

.search-result-item--active,
.search-result-item:hover {
  background: #f1f5f9;
}

.search-result-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.search-result-path {
  font-size: 11px;
  color: #94a3b8;
}

.search-empty {
  margin-top: 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 24px;
}
</style>
