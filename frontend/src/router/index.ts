import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '仪表盘', icon: 'Odometer' },
  },
  {
    path: '/sentiment',
    name: 'Sentiment',
    component: () => import('@/views/SentimentView.vue'),
    meta: { title: '情感分析', icon: 'TrendCharts' },
  },
  {
    path: '/topics',
    name: 'Topics',
    component: () => import('@/views/TopicsView.vue'),
    meta: { title: '主题分析', icon: 'Collection' },
  },
  {
    path: '/topic-sentiment',
    name: 'TopicSentiment',
    component: () => import('@/views/TopicSentimentView.vue'),
    meta: { title: '主题×情感', icon: 'Grid' },
  },
  {
    path: '/trends',
    name: 'Trends',
    component: () => import('@/views/TrendsView.vue'),
    meta: { title: '趋势分析', icon: 'DataLine' },
  },
  {
    path: '/network',
    name: 'Network',
    component: () => import('@/views/NetworkView.vue'),
    meta: { title: '共现网络', icon: 'Connection' },
  },
  {
    path: '/predict',
    name: 'Predict',
    component: () => import('@/views/PredictView.vue'),
    meta: { title: '实时预测', icon: 'MagicStick' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
