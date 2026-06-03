<template>
  <div class="network-page">
    <h2 class="page-title">关键词共现网络</h2>

    <!-- 控制栏 -->
    <el-card style="margin-bottom: 20px">
      <div class="control-bar">
        <div class="control-item">
          <span class="control-label">最小边权重：</span>
          <el-slider
            v-model="minWeight"
            :min="0"
            :max="maxWeight"
            :step="1"
            show-input
            :show-input-controls="false"
            style="width: 300px"
            @change="applyFilter"
          />
        </div>
        <el-button type="primary" @click="resetFilter" :disabled="minWeight === 0">
          重置过滤
        </el-button>
      </div>
    </el-card>

    <!-- 主内容区 -->
    <el-row :gutter="20">
      <!-- 网络图 -->
      <el-col :xs="24" :lg="18">
        <!-- 加载状态 -->
        <template v-if="loading">
          <LoadingCard :rows="12" />
        </template>

        <!-- 错误状态 -->
        <el-alert
          v-else-if="error"
          :title="error"
          type="error"
          show-icon
          :closable="false"
        />

        <!-- 网络图 -->
        <template v-else>
          <el-card>
            <NetworkForceGraph
              :graphData="filteredGraphData"
              @node-click="handleNodeClick"
            />
          </el-card>
        </template>
      </el-col>

      <!-- 右侧节点详情面板 -->
      <el-col :xs="24" :lg="6">
        <el-card v-if="selectedNode" class="node-detail-panel">
          <template #header>
            <span>节点详情</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="节点名称">
              <strong>{{ selectedNode.name }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="节点ID">
              {{ selectedNode.id }}
            </el-descriptions-item>
            <el-descriptions-item label="节点大小">
              {{ selectedNode.symbolSize }}
            </el-descriptions-item>
            <el-descriptions-item label="类别">
              {{ selectedNode.category }}
            </el-descriptions-item>
            <el-descriptions-item label="度中心性">
              {{ selectedNode.degree_centrality?.toFixed(4) ?? '--' }}
            </el-descriptions-item>
            <el-descriptions-item label="介数中心性">
              {{ selectedNode.betweenness_centrality?.toFixed(4) ?? '--' }}
            </el-descriptions-item>
            <el-descriptions-item label="特征向量中心性">
              {{ selectedNode.eigenvector_centrality?.toFixed(4) ?? '--' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card v-else class="node-detail-panel">
          <div class="empty-detail">
            <el-icon :size="36" color="#c0c4cc"><InfoFilled /></el-icon>
            <p style="margin-top: 12px; color: #909399">点击图中节点查看详情</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import client from '@/api/client'
import type { GraphData, GraphNode } from '@/components/charts/NetworkForceGraph.vue'
import NetworkForceGraph from '@/components/charts/NetworkForceGraph.vue'
import LoadingCard from '@/components/common/LoadingCard.vue'
import { InfoFilled } from '@element-plus/icons-vue'

interface NetworkNode extends GraphNode {
  degree_centrality?: number
  betweenness_centrality?: number
  eigenvector_centrality?: number
}

interface RawNetworkData {
  nodes: NetworkNode[]
  edges: { source: string; target: string; weight: number }[]
}

const loading = ref(false)
const error = ref<string | null>(null)
const rawData = ref<RawNetworkData>({ nodes: [], edges: [] })
const minWeight = ref(0)
const maxWeight = ref(10)
const selectedNode = ref<NetworkNode | null>(null)

const filteredGraphData = computed<GraphData>(() => {
  const filteredEdges = rawData.value.edges.filter((e) => e.weight >= minWeight.value)
  const connectedNodeIds = new Set<string>()
  for (const e of filteredEdges) {
    connectedNodeIds.add(e.source)
    connectedNodeIds.add(e.target)
  }
  const filteredNodes = rawData.value.nodes.filter((n) => connectedNodeIds.has(n.id))

  return {
    nodes: filteredNodes.map((n) => ({
      id: n.id,
      name: n.name,
      symbolSize: n.symbolSize,
      category: n.category,
    })),
    edges: filteredEdges,
  }
})

function applyFilter() {
  // 过滤由 computed 自动处理
}

function resetFilter() {
  minWeight.value = 0
}

function handleNodeClick(nodeId: string) {
  const node = rawData.value.nodes.find((n) => n.id === nodeId)
  selectedNode.value = node ?? null
}

async function fetchNetworkData() {
  loading.value = true
  error.value = null
  try {
    const res = await client.get('/network')
    rawData.value = res.data as RawNetworkData
    const edgeWeights = rawData.value.edges.map((e) => e.weight)
    maxWeight.value = Math.max(...edgeWeights, 1)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '获取网络数据失败'
    error.value = msg
    console.error('Network fetch error:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchNetworkData()
})
</script>

<style scoped>
.control-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 14px;
  color: var(--text-regular);
  white-space: nowrap;
}

.node-detail-panel {
  min-height: 300px;
}

.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}
</style>
