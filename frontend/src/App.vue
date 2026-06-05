<template>
  <div class="app-shell">
    <!-- Floating header -->
    <AppHeader />

    <div class="app-body">
      <!-- Floating icon rail -->
      <AppSidebar />

      <!-- Main content -->
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<style scoped>
.app-shell {
  height: 100vh;
  background: #f3f4f6;
  padding: 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.app-body {
  flex: 1;
  display: flex;
  gap: 20px;
  min-height: 0;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}
</style>
