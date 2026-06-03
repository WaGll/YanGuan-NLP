<template>
  <div class="sidebar-wrapper">
    <div class="sidebar-logo" v-if="!collapsed">
      <span class="logo-text">GradCareer</span>
    </div>
    <div class="sidebar-logo sidebar-logo--mini" v-else>
      <span class="logo-text--mini">GC</span>
    </div>
    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
      router
    >
      <el-menu-item index="/dashboard">
        <el-icon><Odometer /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>
      <el-menu-item index="/sentiment">
        <el-icon><TrendCharts /></el-icon>
        <template #title>情感分析</template>
      </el-menu-item>
      <el-menu-item index="/topics">
        <el-icon><Collection /></el-icon>
        <template #title>主题分析</template>
      </el-menu-item>
      <el-menu-item index="/topic-sentiment">
        <el-icon><Grid /></el-icon>
        <template #title>主题×情感</template>
      </el-menu-item>
      <el-menu-item index="/trends">
        <el-icon><DataLine /></el-icon>
        <template #title>趋势分析</template>
      </el-menu-item>
      <el-menu-item index="/network">
        <el-icon><Connection /></el-icon>
        <template #title>共现网络</template>
      </el-menu-item>
      <el-menu-item index="/predict">
        <el-icon><MagicStick /></el-icon>
        <template #title>实时预测</template>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer,
  TrendCharts,
  Collection,
  Grid,
  DataLine,
  Connection,
  MagicStick,
} from '@element-plus/icons-vue'

const props = defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.sidebar-logo--mini {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text--mini {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.el-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}
</style>
