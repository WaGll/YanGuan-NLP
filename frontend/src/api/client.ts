/**
 * Axios HTTP 客户端封装
 */

import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
client.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response
    if (data.code !== undefined && data.code !== 0 && data.code !== 200) {
      console.error(`API Error: ${data.message}`)
      return Promise.reject(new Error(data.message || 'API Error'))
    }
    return data
  },
  (error) => {
    console.error('Network Error:', error.message)
    return Promise.reject(error)
  }
)

export default client
