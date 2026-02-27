import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
})

export interface PortfolioSummary {
  as_of: string
  total_value: number
  cash: number
  positions_value: number
  daily_return: number
  cumulative_return: number
}

export interface Position {
  ticker: string
  quantity: number
  avg_cost: number
  current_price: number
  unrealized_pnl: number
}

export interface NavPoint {
  date: string
  total_value: number
  cash: number
  positions_value: number
  daily_return?: number
  cumulative_return?: number
}

export interface Decision {
  id: number
  ticker: string
  trade_date: string
  final_decision: string
  confidence?: number
  created_at?: string
}

export interface DecisionDetail extends Decision {
  market_report?: string
  sentiment_report?: string
  news_report?: string
  fundamentals_report?: string
  valuation_result?: string
  debate_history?: string
  risk_assessment?: string
  data_links?: Array<{
    id: number
    data_type: string
    data_id: number
  }>
}

export interface DatafeedItem {
  type: 'market' | 'news'
  ticker?: string | null
  trade_date?: string
  source: string
  title?: string | null
  url?: string | null
  published_at?: string | null
  fetched_at: string
}

export async function fetchPortfolioSummary() {
  const res = await api.get<PortfolioSummary>('/portfolio')
  return res.data
}

export async function fetchPositions() {
  const res = await api.get<Position[]>('/positions')
  return res.data
}

export async function fetchNav(limit = 365) {
  const res = await api.get<NavPoint[]>('/nav', { params: { limit } })
  return res.data
}

export async function fetchDecisions(params: {
  ticker?: string
  start_date?: string
  end_date?: string
  limit?: number
}) {
  const res = await api.get<Decision[]>('/decisions', { params })
  return res.data
}

export async function fetchDecisionDetail(id: number) {
  const res = await api.get<DecisionDetail | Record<string, never>>(`/decisions/${id}`)
  return res.data as DecisionDetail
}

export async function fetchDatafeed(params: { type?: string; ticker?: string; limit?: number }) {
  const res = await api.get<DatafeedItem[]>('/datafeed', { params })
  return res.data
}

