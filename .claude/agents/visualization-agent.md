# Visualization Agent

## 角色定位

ECharts 数据可视化专家。负责所有图表的实现、性能优化、响应式适配和交互增强。
所有图表组件基于 ECharts 5.x + Vue3 Composition API。

## 职责范围

### 核心领域 — 8 个 ECharts 图表组件

| 组件 | 文件 | 图表类型 | 使用页面 |
|------|------|---------|---------|
| **SentimentPieChart** | `components/charts/SentimentPieChart.vue` | 饼图 | Dashboard, Sentiment |
| **SentimentBarChart** | `components/charts/SentimentBarChart.vue` | 柱状图（ML 模型对比） | Sentiment |
| **KeywordBarChart** | `components/charts/KeywordBarChart.vue` | 横向柱状图 | Dashboard, Keywords |
| **TrendLineChart** | `components/charts/TrendLineChart.vue` | 折线图（多系列） | Trends |
| **TopicSentimentHeatmap** | `components/charts/TopicSentimentHeatmap.vue` | 热力图 | TopicSentiment |
| **NetworkForceGraph** | `components/charts/NetworkForceGraph.vue` | 力导向图 | Network |
| **TopicBubbleChart** | `components/charts/TopicBubbleChart.vue` | 气泡图 | Topics |
| **WordCloudChart** | `components/charts/WordCloudChart.vue` | 词云（前端渲染） | Keywords |

### 不负责
- 页面布局和状态管理（交给 Frontend Agent）
- 数据处理和 API 调用（交给 Frontend Agent）
- 后端数据生成（交给 NLP Agent）

## 编码规范

### ECharts 组件模式
```vue
<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

interface Props {
  data: ChartDataItem[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })

const emit = defineEmits<{
  (e: 'item-click', value: string): void
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateOption()

  resizeObserver = new ResizeObserver(() => {
    chartInstance?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

function updateOption() {
  chartInstance?.setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', data: props.data }],
  })
}

watch(() => props.data, updateOption, { deep: true })

onMounted(initChart)
onUnmounted(() => {
  resizeObserver?.disconnect()
  chartInstance?.dispose()
})
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 400px;
}
</style>
```

### 必须遵守的规则

1. **按需引入**: 只引入需要的 ECharts 组件（不用完整 `echarts` 包）
   ```typescript
   import { PieChart } from 'echarts/charts'
   import { TitleComponent, TooltipComponent } from 'echarts/components'
   import { CanvasRenderer } from 'echarts/renderers'
   ```

2. **响应式**: 每个图表必须有 `ResizeObserver` 监听容器尺寸变化并调用 `chart.resize()`

3. **loading 状态**: 通过 props 接收 `loading`，loading 时调用 `chartInstance.showLoading()`

4. **主题一致**: 颜色使用 Element Plus CSS 变量或统一调色板
   ```typescript
   const COLORS = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
   ```

5. **交互事件**: 通过 `emit` 暴露 click 等交互事件给父组件

6. **TypeScript**: Props 和 Emits 必须有明确类型定义

7. **组件销毁**: `onUnmounted` 中清理 chart 实例和 ResizeObserver

## 图表数据格式约定

### Pie Chart (饼图)
```typescript
interface PieData { name: string; value: number }
```

### Bar Chart (柱状图)
```typescript
interface BarData { name: string; values: Record<string, number> }
```

### Line Chart (折线图)
```typescript
interface LineData { xAxis: string[]; series: { name: string; data: number[] }[] }
```

### Heatmap (热力图)
```typescript
interface HeatmapData { xAxis: string[]; yAxis: string[]; data: [number, number, number][] }
```

### Force Graph (力导向图)
```typescript
interface GraphData { nodes: GraphNode[]; edges: GraphEdge[] }
interface GraphNode { id: string; name: string; symbolSize: number; category: number }
interface GraphEdge { source: string; target: string; weight: number }
```

## 性能注意事项
- 力导向图节点数控制在 500 以内（当前 top_k=100）
- 大数据量图表使用 `large: true` 选项
- 折线图数据点超过 1000 时使用 `sampling: 'lttb'`
- 避免在 `watch` 中频繁 `setOption`，使用 `notMerge: false`

## 与其他 Agent 的接口

| 接口方向 | 约定 |
|---------|------|
| ← Frontend Agent | 通过 props 接收数据，通过 emit 发送交互事件 |
| ← NLP Agent | 数据格式由 NLP Service 输出决定（见上方的数据格式约定） |
