<template>
  <div
    ref="chartRef"
    class="topic-bubble-chart"
    :class="{ 'is-loading': loading }"
  ></div>
</template>

<script setup lang="ts">
/**
 * TopicBubbleChart — LDA 主题气泡图
 *
 * 每个气泡代表一个主题。X 轴 = 主题序号，Y 轴 = 一致性得分，
 * 气泡大小 = 文档数量。颜色编码区分主题。
 *
 * "Academic Data Lab" 美学：克制的配色、精确的数据呈现、微妙的渐变气泡。
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { ScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([ScatterChart, TitleComponent, TooltipComponent, GridComponent, VisualMapComponent, CanvasRenderer])

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface TopicBubbleDataItem {
  topic_index: number
  label: string | null
  business_label?: string | null
  coherence_score: number | null
  doc_count: number
  keywords: { word: string; weight: number }[]
}

interface Props {
  data: TopicBubbleDataItem[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  (e: 'topic-click', topicIndex: number): void
}>()

// ---------------------------------------------------------------------------
// Chart instance
// ---------------------------------------------------------------------------
const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

// 森林绿系配色 — 5 个主题色
const TOPIC_COLORS = [
  '#006D44', // 森林深绿
  '#1A8A5A', // 中绿
  '#3DA775', // 亮绿
  '#7DCCA5', // 浅绿
  '#A6E7C9', // 薄荷绿
]

// ---------------------------------------------------------------------------
// Build ECharts option
// ---------------------------------------------------------------------------
function buildOption(): echarts.EChartsCoreOption {
  if (!props.data || props.data.length === 0) {
    return {
      title: {
        text: '暂无主题数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#909399', fontSize: 14 },
      },
    }
  }

  const seriesData = props.data.map((item, idx) => {
    const size = Math.max(8, Math.min(80, Math.sqrt(item.doc_count) * 4))
    const color = TOPIC_COLORS[idx % TOPIC_COLORS.length]
    return {
      value: [item.topic_index, item.coherence_score ?? 0, item.doc_count],
      name: item.business_label || item.label || `主题 ${item.topic_index + 1}`,
      symbolSize: size,
      itemStyle: {
        color,
        shadowBlur: 8,
        shadowColor: 'rgba(0,0,0,0.15)',
        shadowOffsetY: 2,
        opacity: 0.88,
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 16,
          shadowColor: 'rgba(0,0,0,0.3)',
          opacity: 1,
        },
      },
      _raw: item,
    }
  })

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: [16, 20],
      textStyle: {
        color: '#2d3748',
        fontSize: 13,
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
      },
      formatter: (params: any) => {
        const d = params.data
        const raw = d._raw as TopicBubbleDataItem
        if (!raw) return ''
        const keywords = raw.keywords
          ?.slice(0, 5)
          .map((k) => k.word)
          .join(' · ')
        const coherence = raw.coherence_score != null ? raw.coherence_score.toFixed(4) : '--'
        return [
          d.name,
          `关键词：${keywords || '--'}`,
          `一致性：${coherence}`,
          `文档数：${raw.doc_count}`,
        ].join('\n')
      },
    },
    grid: {
      left: 60,
      right: 40,
      top: 50,
      bottom: 50,
    },
    xAxis: {
      name: '主题序号',
      nameLocation: 'center',
      nameGap: 35,
      nameTextStyle: {
        color: '#718096',
        fontSize: 12,
        fontWeight: 500,
      },
      type: 'value',
      minInterval: 1,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#a0aec0', fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      name: '一致性得分',
      nameLocation: 'center',
      nameGap: 45,
      nameTextStyle: {
        color: '#718096',
        fontSize: 12,
        fontWeight: 500,
      },
      type: 'value',
      min: 0,
      max: 1,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#a0aec0', fontSize: 11 },
      splitLine: {
        lineStyle: {
          color: '#edf2f7',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        type: 'scatter',
        data: seriesData,
        emphasis: {
          focus: 'series',
          label: {
            show: true,
            position: 'top',
            formatter: (params: any) => params.name,
            color: '#2d3748',
            fontSize: 12,
            fontWeight: 600,
          },
        },
      },
    ],
  }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, undefined, {
    devicePixelRatio: window.devicePixelRatio || 1,
  })
  chartInstance.setOption(buildOption())

  chartInstance.on('click', (params: any) => {
    if (params.data?._raw) {
      emit('topic-click', params.data._raw.topic_index)
    }
  })

  resizeObserver = new ResizeObserver(() => {
    chartInstance?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

onMounted(initChart)

onUnmounted(() => {
  resizeObserver?.disconnect()
  chartInstance?.dispose()
})

watch(
  () => [props.data, props.loading],
  () => {
    if (!chartInstance) return
    if (props.loading) {
      chartInstance.showLoading('default', {
        text: '加载中...',
        color: '#006D44',
        textColor: '#718096',
        maskColor: 'rgba(255,255,255,0.8)',
      })
    } else {
      chartInstance.hideLoading()
      chartInstance.setOption(buildOption(), { notMerge: true })
    }
  },
  { deep: true }
)
</script>

<style scoped>
.topic-bubble-chart {
  width: 100%;
  height: 420px;
  border-radius: 8px;
  background: linear-gradient(135deg, #F4F7F6 0%, #FFFFFF 100%);
}

.topic-bubble-chart.is-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
