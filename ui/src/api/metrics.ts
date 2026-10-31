import { request } from './http'
import type { MetricsSummary, TopSongOut } from './types'

export const top = (limit?: number) =>
  request<TopSongOut[]>(`/api/metrics/top${limit ? `?limit=${limit}` : ''}`)

export const summary = () => request<MetricsSummary>('/api/metrics/summary')
