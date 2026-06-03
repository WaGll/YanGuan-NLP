<template>
  <div class="header-wrapper">
    <div class="header-left">
      <el-icon class="collapse-btn" @click="$emit('toggle')" :size="20">
        <Fold v-if="!collapsed" />
        <Expand v-else />
      </el-icon>
      <h2 class="page-title">{{ pageTitle }}</h2>
    </div>
    <div class="header-right">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-if="pageTitle !== '首页'">
          {{ pageTitle }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Fold, Expand } from '@element-plus/icons-vue'

defineProps<{
  collapsed: boolean
}>()

defineEmits<{
  toggle: []
}>()

const route = useRoute()
const pageTitle = computed(() => {
  const metaTitle = route.meta?.title
  return typeof metaTitle === 'string' ? metaTitle : '仪表盘'
})
</script>

<style scoped>
.header-wrapper {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  cursor: pointer;
  color: var(--text-regular);
}

.collapse-btn:hover {
  color: var(--primary-color);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
}
</style>
