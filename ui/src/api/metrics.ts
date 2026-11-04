import { request } from './http'
import type { CircuitsOut, MetricsSummary, TopArtistOut, TopSongOut } from './types'

export const top = (limit?: number) =>
  request<TopSongOut[]>(`/api/metrics/top${limit ? `?limit=${limit}` : ''}`)

export const summary = () => request<MetricsSummary>('/api/metrics/summary')

export const topArtists = (limit?: number) =>
  request<TopArtistOut[]>(`/api/metrics/top-artists${limit ? `?limit=${limit}` : ''}`)

/** Circuitos de playback-metrics (solo administradores). */
export const circuits = () => request<CircuitsOut>('/api/metrics/circuits')
