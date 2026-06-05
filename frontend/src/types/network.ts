/** 语义网络类型 */

export interface NetworkNode {
  id: string
  name: string
  symbolSize: number
  category: number
  frequency: number
  degree_centrality: number
  betweenness_centrality: number
  closeness_centrality: number
  eigenvector_centrality: number
  pagerank: number
}

export interface NetworkEdge {
  source: string
  target: string
  weight: number
}

export interface NetworkData {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  total_nodes?: number
  total_edges?: number
}

// --- 网络分析指标 ---

export interface CentralNodeItem {
  word: string
  value: number
}

export interface TopCentralNodes {
  degree: CentralNodeItem[]
  betweenness: CentralNodeItem[]
  closeness: CentralNodeItem[]
  pagerank: CentralNodeItem[]
}

export interface CooccurrenceMatrix {
  keywords: string[]
  matrix: number[][]
}

export interface NetworkStatistics {
  node_count: number
  edge_count: number
  density: number
  avg_clustering: number
  connected_components: number
  community_count: number
  modularity: number
}

export interface NetworkMetrics {
  cooccurrence_matrix: CooccurrenceMatrix
  top_central_nodes: TopCentralNodes
  statistics: NetworkStatistics
}
