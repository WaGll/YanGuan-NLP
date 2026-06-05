/** 语义网络 API 模块 */

import client from './client'
import type { NetworkData, NetworkMetrics } from '@/types/network'

export async function getNetworkData(
  minEdgeWeight: number = 2,
  maxNodes: number = 200
): Promise<NetworkData> {
  const res = await client.get('/network', {
    params: { min_edge_weight: minEdgeWeight, max_nodes: maxNodes },
  })
  return res.data ?? { nodes: [], edges: [] }
}

export async function getNetworkMetrics(
  topN: number = 20
): Promise<NetworkMetrics> {
  const res = await client.get('/network/metrics', {
    params: { top_n: topN },
  })
  return (
    res.data ?? {
      cooccurrence_matrix: { keywords: [], matrix: [] },
      top_central_nodes: { degree: [], betweenness: [], closeness: [], pagerank: [] },
      statistics: {
        node_count: 0, edge_count: 0, density: 0, avg_clustering: 0,
        connected_components: 0, community_count: 0, modularity: 0,
      },
    }
  )
}
