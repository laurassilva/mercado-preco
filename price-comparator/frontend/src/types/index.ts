export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
}

export interface AuthToken {
  access_token: string
  token_type: string
  user_id: string
  name: string
  email: string
  role: string
}

export interface Market {
  id: string
  name: string
  url: string
  logo_url: string | null
  integration_type: string
  scraper_class: string
  is_active: boolean
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ProductResult {
  market_id: string | null
  market_name: string
  market_logo: string | null
  product_name: string
  brand: string | null
  quantity: string | null
  price: number
  image_url: string | null
  product_url: string | null
  last_updated: string | null
  difference: number | null
  difference_pct: number | null
  is_cheapest: boolean
}

export interface SearchResponse {
  query: string
  results: ProductResult[]
  total: number
  cheapest_market: string | null
  most_expensive_market: string | null
  avg_price: number | null
  searched_at: string
}

export interface SearchHistory {
  id: string
  query: string
  results_count: number
  created_at: string
  user_name: string | null
  user_email: string | null
}

export interface DashboardStats {
  total_products_monitored: number
  total_markets: number
  total_searches_today: number
  last_update: string | null
  cheapest_market: string | null
  most_expensive_market: string | null
}

export interface MarketSummary {
  market_name: string
  avg_price: number
  products_count: number
}

export interface DashboardData {
  stats: DashboardStats
  recent_searches: Array<{
    query: string
    results_count: number
    created_at: string
    user_name: string | null
  }>
  market_summary: MarketSummary[]
}

export interface ScrapingJob {
  id: string
  market_id: string | null
  query: string | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  results_count: number
  created_at: string
}

// Categories
export interface Category {
  id: string
  name: string
  keywords: string[]
  is_active: boolean
  created_at: string
}

export interface CategoryStats {
  category: string
  products_count: number
  alerts_today: number
  avg_price: number | null
  min_price: number | null
  max_price: number | null
}

// Price Alerts
export interface PriceAlert {
  id: string
  market_product_id: string
  market_id: string
  product_name: string
  old_price: number
  new_price: number
  price_diff: number
  price_diff_pct: number
  alert_type: 'increase' | 'decrease'
  category: string | null
  detected_at: string
  market_name: string | null
}

export interface AlertsSummary {
  total_today: number
  increases_today: number
  decreases_today: number
  biggest_increase: PriceAlert | null
  biggest_decrease: PriceAlert | null
}

// Price History
export interface PriceHistoryEntry {
  price: number
  checked_at: string
}

export interface ProductPriceHistory {
  product_id: string
  product_name: string
  market_id: string
  market_name: string
  current_price: number
  category: string | null
  history: PriceHistoryEntry[]
}

export interface PriceHistorySearchResponse {
  query: string
  period_days: number
  products: ProductPriceHistory[]
  stats: {
    min_price: number | null
    max_price: number | null
    avg_price: number | null
    total_changes: number
  }
}
