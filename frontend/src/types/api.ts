/** 通用 API 响应类型 */

export interface APIResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T = unknown> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
