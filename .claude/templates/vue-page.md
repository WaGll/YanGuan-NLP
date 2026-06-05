# Template: 新建 Vue 页面

## 使用说明

复制此模板创建新的 Vue 页面。替换 `{{placeholders}}`。

## 文件位置
`frontend/src/views/{{PageName}}View.vue`

## 模板

```vue
<template>
  <div class="{{page-name}}-page">
    <h2 class="page-title">{{页面标题}}</h2>

    <!-- 加载状态 -->
    <template v-if="loading">
      <LoadingCard :rows="8" />
    </template>

    <!-- 错误状态 -->
    <template v-else-if="error">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
      <el-button type="primary" style="margin-top: 16px" @click="fetchData">
        重新加载
      </el-button>
    </template>

    <!-- 空数据状态 -->
    <template v-else-if="!data || data.length === 0">
      <el-card>
        <el-empty description="暂无数据">
          <el-button type="primary" @click="fetchData">
            刷新数据
          </el-button>
        </el-empty>
      </el-card>
    </template>

    <!-- 正常内容 -->
    <template v-else>
      <el-card>
        <!-- 内容区域 -->
        <div class="content-area">
          <!-- 在这里放置图表组件或其他内容 -->
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * {{页面中文名}}页面
 *
 * 功能描述: {{功能描述}}
 */
import { ref, computed, onMounted } from 'vue'
import { get{{DataName}} } from '@/api/{{api-module}}'
import type { {{DataType}} } from '@/types/{{type-file}}'
import LoadingCard from '@/components/common/LoadingCard.vue'

// ---------------------------------------------------------------------------
// 状态
// ---------------------------------------------------------------------------
const data = ref<{{DataType}}[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// ---------------------------------------------------------------------------
// 计算属性
// ---------------------------------------------------------------------------
const hasData = computed(() => data.value && data.value.length > 0)

// ---------------------------------------------------------------------------
// 方法
// ---------------------------------------------------------------------------
async function fetchData() {
  loading.value = true
  error.value = null
  try {
    data.value = await get{{DataName}}()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '数据加载失败'
    error.value = msg
    console.error('{{PageName}} fetch error:', err)
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// 生命周期
// ---------------------------------------------------------------------------
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.{{page-name}}-page {
  padding: 0;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 20px;
}

.content-area {
  min-height: 400px;
}
</style>
```

## 清单

添加新页面时需要检查：
- [ ] 文件放在 `frontend/src/views/` 下，命名 `XxxView.vue`
- [ ] 页面覆盖 loading / error / empty / data 四种状态
- [ ] 使用 `<script setup lang="ts">`
- [ ] API 调用有 try/catch 错误处理
- [ ] 错误信息显示给用户，同时 console.error 记录
- [ ] 提供"重新加载"按钮
- [ ] 在 `frontend/src/router/index.ts` 中添加路由（懒加载）
- [ ] 在 `frontend/src/components/layout/AppSidebar.vue` 中添加导航项
- [ ] 如有 API 调用，创建对应的 `frontend/src/api/{{api-module}}.ts`
- [ ] 如有状态管理，创建对应的 `frontend/src/stores/{{store-name}}.ts`
