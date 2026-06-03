<template>
  <el-container class="app-container">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="app-sidebar">
      <AppSidebar :collapsed="isCollapsed" @toggle="isCollapsed = !isCollapsed" />
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <AppHeader :collapsed="isCollapsed" @toggle="isCollapsed = !isCollapsed" />
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'

const isCollapsed = ref(false)
</script>

<style scoped>
.app-container {
  height: 100vh;
}
.app-sidebar {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  display: flex;
  align-items: center;
}
.app-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
