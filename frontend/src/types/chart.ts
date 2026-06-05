/** 图表通用类型 */

export interface ChartDimension {
  name: string
  value: number
}

export interface TimeSeriesPoint {
  date: string
  value: number
}

export interface CategoryValue {
  category: string
  value: number
  [key: string]: unknown
}
