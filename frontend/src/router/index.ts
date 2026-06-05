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
    meta: { title: '仪表盘', nav: true, label: 'Overview' },
  },
  {
    path: '/sentiment',
    name: 'Sentiment',
    component: () => import('@/views/SentimentView.vue'),
    meta: { title: '情感分析', nav: true, label: 'Sentiment' },
  },
  {
    path: '/topics',
    name: 'Topics',
    component: () => import('@/views/TopicsView.vue'),
    meta: { title: '主题分析', nav: true, label: 'Topics' },
  },
  {
    path: '/topic-sentiment',
    name: 'TopicSentiment',
    component: () => import('@/views/TopicSentimentView.vue'),
    meta: { title: '主题×情感', nav: false },
  },
  {
    path: '/trends',
    name: 'Trends',
    component: () => import('@/views/TrendsView.vue'),
    meta: { title: '趋势分析', nav: true, label: 'Trends' },
  },
  {
    path: '/network',
    name: 'Network',
    component: () => import('@/views/NetworkView.vue'),
    meta: { title: '共现网络', nav: true, label: 'Network' },
  },
  {
    path: '/network-analytics',
    name: 'NetworkAnalytics',
    component: () => import('@/views/NetworkAnalyticsView.vue'),
    meta: { title: '网络分析', nav: false },
  },
  {
    path: '/predict',
    name: 'Predict',
    component: () => import('@/views/PredictView.vue'),
    meta: { title: '实时预测', nav: true, label: 'Forecast' },
  },
  {
    path: '/emotes',
    name: 'Emotes',
    component: () => import('@/views/EmoteView.vue'),
    meta: { title: '表情分析', nav: false },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
