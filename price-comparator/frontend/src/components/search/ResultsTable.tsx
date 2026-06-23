'use client'
import { useState, useRef, useMemo, useEffect } from 'react'
import { ExternalLink, TrendingDown, TrendingUp, Award, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, X, BarChart3 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { ProductResult, SearchResponse, ProductPriceHistory } from '@/types'
import { formatBRL, formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import api from '@/services/api'

type SortField = 'price' | 'market_name' | 'product_name' | 'difference'
type SortDir = 'asc' | 'desc'
const PAGE_SIZE_OPTIONS = [10, 15, 20, 50] as const
const HISTORY_PERIODS = ['7d', '15d', '30d', '60d', '90d'] as const

interface Props {
  data: SearchResponse
  onExportPDF: () => void
  onExportExcel: () => void
  onExportCSV: () => void
}

export default function ResultsTable({ data, onExportPDF, onExportExcel, onExportCSV }: Props) {
  const [sort, setSort] = useState<{ field: SortField; dir: SortDir }>({ field: 'price', dir: 'asc' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<number>(10)
  const [productColWidth, setProductColWidth] = useState(260)
  const dragRef = useRef<{ startX: number; startW: number } | null>(null)
  const [historyProduct, setHistoryProduct] = useState<ProductResult | null>(null)

  useEffect(() => { setPage(1) }, [data.query])

  const toggleSort = (field: SortField) => {
    setSort((prev) =>
      prev.field === field ? { field, dir: prev.dir === 'asc' ? 'desc' : 'asc' } : { field, dir: 'asc' }
    )
  }

  const sorted = useMemo(() => [...data.results].sort((a, b) => {
    const va = sort.field === 'price' ? Number(a.price)
      : sort.field === 'difference' ? Number(a.difference ?? 0)
      : String(a[sort.field]).toLowerCase()
    const vb = sort.field === 'price' ? Number(b.price)
      : sort.field === 'difference' ? Number(b.difference ?? 0)
      : String(b[sort.field]).toLowerCase()
    if (va < vb) return sort.dir === 'asc' ? -1 : 1
    if (va > vb) return sort.dir === 'asc' ? 1 : -1
    return 0
  }), [data.results, sort])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const paginatedItems = sorted.slice((safePage - 1) * pageSize, safePage * pageSize)

  const handlePageSize = (size: number) => {
    setPageSize(size)
    setPage(1)
  }

  const onResizePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault()
    const el = e.currentTarget
    el.setPointerCapture(e.pointerId)
    dragRef.current = { startX: e.clientX, startW: productColWidth }
    const onMove = (ev: PointerEvent) => {
      if (!dragRef.current) return
      const delta = ev.clientX - dragRef.current.startX
      setProductColWidth(Math.max(160, dragRef.current.startW + delta))
    }
    const onUp = () => {
      dragRef.current = null
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerup', onUp)
    }
    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerup', onUp)
  }

  const SortBtn = ({ field, label }: { field: SortField; label: string }) => {
    const active = sort.field === field
    return (
      <button
        className={cn('flex items-center gap-1 hover:text-gray-900 transition-colors', active ? 'text-brand-700 font-bold' : '')}
        onClick={() => toggleSort(field)}
      >
        {label}
        {active ? (
          sort.dir === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
        ) : (
          <ArrowUpDown className="w-3 h-3 opacity-40" />
        )}
      </button>
    )
  }

  const maxDiff = (data.results[data.results.length - 1]?.price ?? 0) - (data.results[0]?.price ?? 0)

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 md:p-4">
          <div className="flex items-center gap-1.5 text-green-700 text-xs font-medium mb-1">
            <TrendingDown className="w-3 h-3" /> Menor Preço
          </div>
          <p className="font-bold text-green-800 text-sm md:text-base">{formatBRL(data.results[0]?.price)}</p>
          <p className="text-xs text-green-600 truncate">{data.results[0]?.market_name}</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 md:p-4">
          <div className="flex items-center gap-1.5 text-red-700 text-xs font-medium mb-1">
            <TrendingUp className="w-3 h-3" /> Maior Preço
          </div>
          <p className="font-bold text-red-800 text-sm md:text-base">{formatBRL(data.results[data.results.length - 1]?.price)}</p>
          <p className="text-xs text-red-600 truncate">{data.results[data.results.length - 1]?.market_name}</p>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 md:p-4">
          <div className="flex items-center gap-1.5 text-blue-700 text-xs font-medium mb-1">
            <Award className="w-3 h-3" /> Preço Médio
          </div>
          <p className="font-bold text-blue-800 text-sm md:text-base">{formatBRL(data.avg_price)}</p>
          <p className="text-xs text-blue-600">{data.total} resultado(s)</p>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-3 md:p-4">
          <div className="text-purple-700 text-xs font-medium mb-1">Diferença Máxima</div>
          <p className="font-bold text-purple-800 text-sm md:text-base">{formatBRL(maxDiff)}</p>
          <p className="text-xs text-purple-600">menor ↔ maior</p>
        </div>
      </div>

      {/* Export + info */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-gray-600">
          <span className="font-semibold">{data.total}</span> resultado(s) · clique no produto para ver histórico
        </p>
        <div className="flex gap-2">
          <button onClick={onExportPDF} className="btn-secondary text-xs py-1.5 px-3">PDF</button>
          <button onClick={onExportExcel} className="btn-secondary text-xs py-1.5 px-3">Excel</button>
          <button onClick={onExportCSV} className="btn-secondary text-xs py-1.5 px-3">CSV</button>
        </div>
      </div>

      <PaginationBar page={safePage} totalPages={totalPages} pageSize={pageSize} totalItems={sorted.length} onPageChange={setPage} onPageSizeChange={handlePageSize} />

      {/* MOBILE: cards */}
      <div className="md:hidden space-y-3">
        {paginatedItems.map((item, idx) => (
          <div
            key={idx}
            onClick={() => setHistoryProduct(item)}
            className={cn(
              'rounded-xl border p-4 space-y-2 cursor-pointer hover:shadow-md transition-shadow',
              item.is_cheapest ? 'bg-green-50 border-green-300' : 'bg-white border-gray-200'
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-sm leading-tight">{item.product_name}</p>
                <p className="text-xs text-gray-500 mt-0.5">{item.market_name}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className={cn('font-bold text-lg', item.is_cheapest ? 'text-green-700' : 'text-gray-900')}>
                  {formatBRL(item.price)}
                </p>
                {item.is_cheapest && <span className="text-xs text-green-600 font-medium">✓ Mais barato</span>}
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>
                {item.difference != null && item.difference > 0
                  ? <span className="text-red-500">+{formatBRL(item.difference)} ({item.difference_pct?.toFixed(1)}%)</span>
                  : <span className="text-green-600">Menor preço</span>}
              </span>
              <span className="flex items-center gap-1 text-brand-600"><BarChart3 className="w-3 h-3" /> Ver histórico</span>
            </div>
          </div>
        ))}
      </div>

      {/* DESKTOP: tabela */}
      <div className="hidden md:block table-container">
        <table className="data-table" style={{ tableLayout: 'fixed', width: '100%', minWidth: '700px' }}>
          <colgroup>
            <col style={{ width: '38px' }} />
            <col style={{ width: '190px' }} />
            <col style={{ width: `${productColWidth}px` }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '120px' }} />
            <col style={{ width: '80px' }} />
          </colgroup>
          <thead>
            <tr>
              <th style={{ whiteSpace: 'nowrap' }}>#</th>
              <th style={{ whiteSpace: 'nowrap' }}><SortBtn field="market_name" label="Mercado" /></th>
              <th style={{ position: 'relative', whiteSpace: 'nowrap', paddingRight: '20px' }}>
                <SortBtn field="product_name" label="Produto" />
                <div
                  onPointerDown={onResizePointerDown}
                  style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '8px', cursor: 'col-resize', backgroundColor: '#3b82f6', opacity: 0.5, borderRadius: '0 4px 4px 0', userSelect: 'none', touchAction: 'none' }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}
                  title="Arraste para redimensionar"
                />
              </th>
              <th style={{ whiteSpace: 'nowrap' }}>Qtd</th>
              <th style={{ whiteSpace: 'nowrap' }}><SortBtn field="price" label="Preço" /></th>
              <th style={{ whiteSpace: 'nowrap' }}><SortBtn field="difference" label="Diferença" /></th>
              <th style={{ whiteSpace: 'nowrap' }}>Link</th>
            </tr>
          </thead>
          <tbody>
            {paginatedItems.map((item, idx) => (
              <tr key={idx} className={cn(item.is_cheapest && 'cheapest', 'cursor-pointer hover:bg-blue-50/50 transition-colors')} onClick={() => setHistoryProduct(item)}>
                <td className="text-gray-400 text-xs">{(safePage - 1) * pageSize + idx + 1}</td>
                <td>
                  <div className="flex items-center gap-1.5">
                    {item.is_cheapest && <span className="badge-green text-xs whitespace-nowrap">✓ Mais barato</span>}
                    <span className="font-medium text-gray-800" style={{ wordBreak: 'break-word' }}>{item.market_name}</span>
                  </div>
                </td>
                <td style={{ overflow: 'hidden', paddingRight: '12px' }}>
                  <p className="font-medium text-gray-800 text-brand-700 hover:underline" style={{ wordBreak: 'break-word', whiteSpace: 'normal', lineHeight: '1.4' }}>
                    {item.product_name}
                  </p>
                  {item.brand && <p className="text-xs text-gray-400 mt-0.5">{item.brand}</p>}
                </td>
                <td className="text-gray-500 text-xs" style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>{item.quantity || '-'}</td>
                <td>
                  <span className={cn('font-bold whitespace-nowrap', item.is_cheapest ? 'text-green-700' : 'text-gray-800')}>{formatBRL(item.price)}</span>
                </td>
                <td className="whitespace-nowrap">
                  {item.difference != null && item.difference > 0 ? (
                    <span className="text-red-500 text-sm">
                      +{formatBRL(item.difference)}
                      {item.difference_pct != null && <span className="text-xs ml-1 text-red-400">({item.difference_pct.toFixed(1)}%)</span>}
                    </span>
                  ) : (
                    <span className="text-green-600 text-sm font-medium">Menor</span>
                  )}
                </td>
                <td>
                  {item.product_url ? (
                    <a href={item.product_url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-800 font-medium whitespace-nowrap">
                      Ver <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <PaginationBar page={safePage} totalPages={totalPages} pageSize={pageSize} totalItems={sorted.length} onPageChange={setPage} onPageSizeChange={handlePageSize} />

      {/* Product History Modal */}
      {historyProduct && (
        <ProductHistoryModal product={historyProduct} onClose={() => setHistoryProduct(null)} />
      )}
    </div>
  )
}


function ProductHistoryModal({ product, onClose }: { product: ProductResult; onClose: () => void }) {
  const [history, setHistory] = useState<ProductPriceHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState('30d')

  useEffect(() => {
    setLoading(true)
    const productId = (product as ProductResult & { market_product_id?: string }).market_product_id
    if (productId) {
      api.get<ProductPriceHistory>(`/price-history/product/${productId}`, { params: { period } })
        .then(({ data }) => setHistory(data))
        .catch(() => setHistory(null))
        .finally(() => setLoading(false))
    } else {
      api.get(`/price-history/search`, { params: { q: product.product_name, period, market_id: product.market_id || undefined } })
        .then(({ data }) => {
          const match = data.products?.find((p: ProductPriceHistory) =>
            p.market_name === product.market_name && p.product_name === product.product_name
          ) || data.products?.[0] || null
          setHistory(match)
        })
        .catch(() => setHistory(null))
        .finally(() => setLoading(false))
    }
  }, [product, period])

  const chartData = history?.history.map(h => ({
    date: new Date(h.checked_at).toLocaleDateString('pt-BR'),
    price: h.price,
  })) || []

  const prices = history?.history.map(h => h.price) || []
  const minPrice = prices.length ? Math.min(...prices) : null
  const maxPrice = prices.length ? Math.max(...prices) : null
  const avgPrice = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b">
          <div>
            <h3 className="font-bold text-gray-900 text-lg">{product.product_name}</h3>
            <p className="text-sm text-gray-500">{product.market_name}</p>
            <p className="text-xl font-bold text-brand-700 mt-1">{formatBRL(product.price)}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Period selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Período:</span>
            {HISTORY_PERIODS.map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={cn('px-3 py-1 rounded-full text-xs font-medium transition-colors',
                  period === p ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}>
                {p.replace('d', ' dias')}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-400">Carregando histórico...</div>
          ) : !history || history.history.length <= 1 ? (
            <div className="text-center py-8">
              <BarChart3 className="w-10 h-10 mx-auto mb-2 text-gray-300" />
              <p className="text-gray-500 text-sm">Sem histórico de variações neste período</p>
              <p className="text-gray-400 text-xs mt-1">O histórico é registrado quando o preço muda durante as coletas</p>
            </div>
          ) : (
            <>
              {/* Stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <p className="text-xs text-green-600">Menor</p>
                  <p className="font-bold text-green-800">{minPrice != null ? formatBRL(minPrice) : '-'}</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-xs text-blue-600">Médio</p>
                  <p className="font-bold text-blue-800">{avgPrice != null ? formatBRL(avgPrice) : '-'}</p>
                </div>
                <div className="bg-red-50 rounded-lg p-3 text-center">
                  <p className="text-xs text-red-600">Maior</p>
                  <p className="font-bold text-red-800">{maxPrice != null ? formatBRL(maxPrice) : '-'}</p>
                </div>
              </div>

              {/* Chart */}
              {chartData.length > 1 && (
                <div className="bg-gray-50 rounded-xl p-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `R$${v}`} domain={['auto', 'auto']} />
                      <Tooltip formatter={(value: number) => formatBRL(value)} labelStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="price" stroke="#2563eb" strokeWidth={2} dot={{ r: 4, fill: '#2563eb' }} name="Preço" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Timeline */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Histórico de Preços</h4>
                <div className="divide-y divide-gray-100">
                  {history.history.map((h, i) => {
                    const prev = i > 0 ? history.history[i - 1].price : null
                    const diff = prev != null ? h.price - prev : null
                    return (
                      <div key={i} className="flex items-center justify-between py-2">
                        <span className="text-sm text-gray-500">{formatDate(h.checked_at)}</span>
                        <div className="flex items-center gap-3">
                          {diff != null && diff !== 0 && (
                            <span className={cn('text-xs font-medium', diff > 0 ? 'text-red-500' : 'text-green-500')}>
                              {diff > 0 ? '+' : ''}{formatBRL(diff)}
                            </span>
                          )}
                          <span className="font-semibold text-gray-800">{formatBRL(h.price)}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}


function PaginationBar({ page, totalPages, pageSize, totalItems, onPageChange, onPageSizeChange }: {
  page: number; totalPages: number; pageSize: number; totalItems: number; onPageChange: (p: number) => void; onPageSizeChange: (s: number) => void
}) {
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, totalItems)
  const pageButtons = useMemo(() => {
    const pages: (number | '...')[] = []
    if (totalPages <= 7) { for (let i = 1; i <= totalPages; i++) pages.push(i) }
    else {
      pages.push(1)
      if (page > 3) pages.push('...')
      for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) pages.push(i)
      if (page < totalPages - 2) pages.push('...')
      pages.push(totalPages)
    }
    return pages
  }, [page, totalPages])

  if (totalItems <= PAGE_SIZE_OPTIONS[0]) return null

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 py-2">
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <span>{start}–{end} de {totalItems}</span>
        <span className="text-gray-300">|</span>
        <span className="text-gray-500">Exibir:</span>
        {PAGE_SIZE_OPTIONS.map((size) => (
          <button key={size} onClick={() => onPageSizeChange(size)}
            className={cn('px-2 py-0.5 rounded text-sm font-medium transition-colors', pageSize === size ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200')}>
            {size}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1">
        <button onClick={() => onPageChange(1)} disabled={page <= 1} className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors" title="Primeira página"><ChevronsLeft className="w-4 h-4" /></button>
        <button onClick={() => onPageChange(page - 1)} disabled={page <= 1} className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors" title="Página anterior"><ChevronLeft className="w-4 h-4" /></button>
        {pageButtons.map((p, i) => p === '...' ? (
          <span key={`dots-${i}`} className="px-1.5 text-gray-400 text-sm">...</span>
        ) : (
          <button key={p} onClick={() => onPageChange(p)} className={cn('min-w-[32px] h-8 rounded text-sm font-medium transition-colors', page === p ? 'bg-brand-600 text-white' : 'hover:bg-gray-100 text-gray-700')}>{p}</button>
        ))}
        <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages} className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors" title="Próxima página"><ChevronRight className="w-4 h-4" /></button>
        <button onClick={() => onPageChange(totalPages)} disabled={page >= totalPages} className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors" title="Última página"><ChevronsRight className="w-4 h-4" /></button>
      </div>
    </div>
  )
}
