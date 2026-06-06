<template>
  <nav class="icon-rail">
    <!-- Logo -->
    <router-link to="/dashboard" class="icon-rail__logo">
      <span class="icon-rail__logo-text">YG</span>
    </router-link>

    <!-- Navigation icons -->
    <div class="icon-rail__nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="icon-rail__item"
        :class="{ 'icon-rail__item--active': isActive(item.path) }"
        :title="item.label"
      >
        <el-icon :size="20">
          <component :is="item.icon" />
        </el-icon>
      </router-link>
    </div>

    <!-- Divider -->
    <div class="icon-rail__divider"></div>

    <!-- Utility icons -->
    <div class="icon-rail__utils">
      <button class="icon-rail__item" title="Search (⌘K)" @click="openSearch">
        <el-icon :size="18"><Search /></el-icon>
      </button>
      <button class="icon-rail__item" title="Settings">
        <el-icon :size="18"><Setting /></el-icon>
      </button>
    </div>

    <!-- User -->
    <div class="icon-rail__user">
      <span class="icon-rail__avatar">WG</span>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  Odometer,
  Collection,
  TrendCharts,
  DataLine,
  Connection,
  MagicStick,
  Search,
  Setting,
} from '@element-plus/icons-vue'

const route = useRoute()

const navItems = [
  { path: '/dashboard', label: 'Overview',   icon: Odometer },
  { path: '/topics',    label: 'Topics',     icon: Collection },
  { path: '/sentiment', label: 'Sentiment',  icon: TrendCharts },
  { path: '/trends',    label: 'Trends',     icon: DataLine },
  { path: '/network',   label: 'Network',    icon: Connection },
  { path: '/predict',   label: 'Forecast',   icon: MagicStick },
]

function isActive(path: string): boolean {
  if (path === '/dashboard') return route.path === '/dashboard' || route.path === '/'
  return route.path.startsWith(path)
}

function openSearch() {
  window.dispatchEvent(new CustomEvent('open-search'))
}
</script>

<style scoped>
.icon-rail {
  width: 72px;
  flex-shrink: 0;
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  gap: 2px;
}

/* ── Logo ── */
.icon-rail__logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #16a34a;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  margin-bottom: 12px;
}

.icon-rail__logo-text {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

/* ── Nav items ── */
.icon-rail__nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.icon-rail__item {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
  text-decoration: none;
  border: none;
  background: transparent;
}

.icon-rail__item:hover {
  background: #f0fdf4;
  color: #16a34a;
}

.icon-rail__item--active {
  background: #16a34a;
  color: #ffffff;
}

.icon-rail__item--active:hover {
  background: #15803d;
  color: #ffffff;
}

/* ── Divider ── */
.icon-rail__divider {
  width: 28px;
  height: 1px;
  background: #e8eaed;
  margin: 4px 0;
}

/* ── Utils ── */
.icon-rail__utils {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

/* ── User avatar ── */
.icon-rail__user {
  margin-top: 8px;
}

.icon-rail__avatar {
  width: 32px;
  height: 32px;
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

.icon-rail__avatar:hover {
  background: #e2e8f0;
  color: #1e293b;
}
</style>
