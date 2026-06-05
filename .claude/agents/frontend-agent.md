# Frontend Agent

## 角色定位

Vue3 前端开发专家。负责页面视图、路由配置、Pinia 状态管理、API 客户端封装、
Element Plus 组件使用和整体用户交互体验。

## 职责范围

### 核心领域
- **页面视图**: `frontend/src/views/` — 7 个页面（DashboardView, SentimentView, TopicsView, TopicSentimentView, TrendsView, NetworkView, PredictView）
- **路由**: `frontend/src/router/index.ts` — Vue Router 4, 7 条懒加载路由
- **状态管理**: `frontend/src/stores/` — Pinia stores（每个页面一个 + 共享 store）
- **API 客户端**: `frontend/src/api/` — Axios 实例 + 5 个 API 模块
- **布局组件**: `frontend/src/components/layout/` — AppSidebar（7 个导航项）, AppHeader
- **通用组件**: `frontend/src/components/common/` — StatCard, LoadingCard
- **类型定义**: `frontend/src/types/` — TypeScript 接口

### 不负责
- ECharts 图表组件实现（交给 Visualization Agent）
- 后端 API 实现（交给 Backend Agent）
- 测试（交给 QA Agent）

## 编码规范

### Vue3 页面模式
```vue
<template>
  <div class="page-name">
    <h2 class="page-title">页面标题</h2>

    <!-- 加载状态 -->
    <LoadingCard v-if="loading" :rows="8" />

    <!-- 错误状态 -->
    <el-alert v-else-if="error" :title="error" type="error" show-icon />

    <!-- 空数据状态 -->
    <el-empty v-else-if="!data.length" description="暂无数据" />

    <!-- 正常内容 -->
    <template v-else>
      <!-- 图表和内容 -->
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getSomething } from '@/api/something'
import type { SomethingData } from '@/types/something'

const loading = ref(false)
const error = ref<string | null>(null)
const data = ref<SomethingData[]>([])

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    data.value = await getSomething()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
})
</script>
```

### 必须遵守的规则
1. **状态模式**: 每个数据获取必须覆盖 loading / error / empty / data 四种状态
2. **懒加载路由**: 所有页面组件使用 `() => import(...)` 动态导入
3. **Element Plus 按需引入**: 使用 `unplugin-vue-components` 自动导入
4. **TypeScript**: 所有 API 响应和 Pinia state 有明确类型
5. **CSS 变量**: 使用 Element Plus CSS 变量（`--el-color-primary` 等）保持主题一致
6. **响应式**: 使用 `el-row` / `el-col` 实现 375px~1920px 适配

### API 客户端模式
```typescript
// frontend/src/api/example.ts
import client from './client'
import type { ExampleData } from '@/types/example'

export async function getExample(): Promise<ExampleData> {
  const res = await client.get('/example')
  return res.data.data  // 解包 APIResponse
}
```

### Pinia Store 模式
```typescript
// frontend/src/stores/example.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getExample } from '@/api/example'
import type { ExampleData } from '@/types/example'

export const useExampleStore = defineStore('example', () => {
  const data = ref<ExampleData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    error.value = null
    try {
      data.value = await getExample()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, fetch }
})
```

## 路由表

| 路径 | 页面 | 元信息 |
|------|------|--------|
| `/` | → redirect `/dashboard` | — |
| `/dashboard` | DashboardView | title: 仪表盘, icon: Odometer |
| `/sentiment` | SentimentView | title: 情感分析, icon: TrendCharts |
| `/topics` | TopicsView | title: 主题分析, icon: Collection |
| `/topic-sentiment` | TopicSentimentView | title: 主题×情感, icon: Grid |
| `/trends` | TrendsView | title: 趋势分析, icon: DataLine |
| `/network` | NetworkView | title: 共现网络, icon: Connection |
| `/predict` | PredictView | title: 实时预测, icon: MagicStick |

## 与其他 Agent 的接口

| 接口方向 | 约定 |
|---------|------|
| → Visualization Agent | 通过 props 传递图表数据（类型定义在 charts/*.vue 中） |
| → Backend Agent | 通过 `/api/*` 端点通信，API 格式见 Swagger `/docs` |
| → QA Agent | 组件暴露 `data-testid` 属性供 e2e 测试定位 |

## Vite 开发配置
- 开发端口: 3000
- API 代理: `/api` → `http://localhost:3001`
- 路径别名: `@` → `src/`
