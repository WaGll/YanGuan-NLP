<template>
  <header class="app-header">
    <!-- Left: Navigation pills -->
    <nav class="header-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="header-nav__pill"
        :class="{ 'header-nav__pill--active': isActive(item.path) }"
      >
        {{ item.label }}
      </router-link>
    </nav>

    <!-- Right: Context + actions -->
    <div class="header-right">
      <span class="header-pill">
        <span class="header-pill__dot"></span>
        考研评论
      </span>
      <span class="header-meta">2024-12</span>

      <el-select
        v-model="selectedModel"
        size="small"
        class="header-select"
        @change="handleModelChange"
      >
        <el-option label="BERTopic" value="bertopic" />
        <el-option label="LDA" value="lda" />
      </el-select>

      <span class="header-avatar">WG</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const selectedModel = ref<'bertopic' | 'lda'>('bertopic')

const navItems = [
  { path: '/dashboard', label: 'Overview' },
  { path: '/topics',    label: 'Topics' },
  { path: '/sentiment', label: 'Sentiment' },
  { path: '/trends',    label: 'Trends' },
  { path: '/network',   label: 'Network' },
  { path: '/predict',   label: 'Forecast' },
]

function isActive(path: string): boolean {
  if (path === '/dashboard') return route.path === '/dashboard' || route.path === '/'
  return route.path.startsWith(path)
}

function handleModelChange(value: 'bertopic' | 'lda') {
  window.dispatchEvent(new CustomEvent('model-change', { detail: value }))
}
</script>

<style scoped>
.app-header {
  height: 72px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

/* ── Nav pills (left-aligned) ── */
.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-nav__pill {
  height: 36px;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  text-decoration: none;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.header-nav__pill:hover {
  color: #1e293b;
  background: #f8fafc;
}

.header-nav__pill--active {
  background: #e2e8f0;
  color: #0f172a;
  font-weight: 600;
}

.header-nav__pill--active:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* ── Right: Context ── */
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.header-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 9999px;
  background: #f1f5f9;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  white-space: nowrap;
}

.header-pill__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}

.header-meta {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
}

.header-select {
  width: 100px;
}

.header-select :deep(.el-input__wrapper) {
  height: 28px;
  font-size: 11px;
  border-radius: 8px !important;
}

.header-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.header-avatar:hover {
  background: #e2e8f0;
  color: #1e293b;
}
</style>
