'use client'
import { useState, useRef, useMemo, useEffect } from 'react'
import { ExternalLink, TrendingDown, TrendingUp, Award, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import type { ProductResult, SearchResponse } from '@/types'
import { formatBRL, formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'

type SortField = 'price' | 'market_name' | 'product_name' | 'difference'
type SortDir = 'asc' | 'desc'
const PAGE_SIZE_OPTIONS = [10, 15, 20, 50] as const

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

  // setPointerCapture garante que o drag continua mesmo saindo do elemento
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
          <span className="font-semibold">{data.total}</span> resultado(s) · ordenado por preço
        </p>
        <div className="flex gap-2">
          <button onClick={onExportPDF} className="btn-secondary text-xs py-1.5 px-3">PDF</button>
          <button onClick={onExportExcel} className="btn-secondary text-xs py-1.5 px-3">Excel</button>
          <button onClick={onExportCSV} className="btn-secondary text-xs py-1.5 px-3">CSV</button>
        </div>
      </div>

      {/* Pagination controls */}
      <PaginationBar
        page={safePage}
        totalPages={totalPages}
        pageSize={pageSize}
        totalItems={sorted.length}
        onPageChange={setPage}
        onPageSizeChange={handlePageSize}
      />

      {/* MOBILE: cards */}
      <div className="md:hidden space-y-3">
        {paginatedItems.map((item, idx) => (
          <div
            key={idx}
            className={cn(
              'rounded-xl border p-4 space-y-2',
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
              {item.product_url && (
                <a href={item.product_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-brand-600 hover:text-brand-800 font-medium">
                  Ver produto <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* DESKTOP: tabela */}
      <div className="hidden md:block table-container">
        {/* Dica de redimensionamento */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 border-b border-blue-100 text-xs text-blue-600">
          <span>↔</span>
          <span>Arraste a barra azul na coluna <strong>Produto</strong> para ajustar a largura</span>
        </div>

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

              {/* Coluna Produto com handle de resize na borda direita */}
              <th style={{ position: 'relative', whiteSpace: 'nowrap', paddingRight: '20px' }}>
                <SortBtn field="product_name" label="Produto" />
                {/* Handle: barra vertical azul arrastável */}
                <div
                  onPointerDown={onResizePointerDown}
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 0,
                    bottom: 0,
                    width: '8px',
                    cursor: 'col-resize',
                    backgroundColor: '#3b82f6',
                    opacity: 0.5,
                    borderRadius: '0 4px 4px 0',
                    userSelect: 'none',
                    touchAction: 'none',
                  }}
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
              <tr key={idx} className={cn(item.is_cheapest && 'cheapest')}>
                <td className="text-gray-400 text-xs">{(safePage - 1) * pageSize + idx + 1}</td>
                <td>
                  <div className="flex items-center gap-1.5">
                    {item.is_cheapest && (
                      <span className="badge-green text-xs whitespace-nowrap">✓ Mais barato</span>
                    )}
                    <span className="font-medium text-gray-800" style={{ wordBreak: 'break-word' }}>
                      {item.market_name}
                    </span>
                  </div>
                </td>
                {/* Célula do produto: sem truncate, texto quebra em linhas */}
                <td style={{ overflow: 'hidden', paddingRight: '12px' }}>
                  <p
                    className="font-medium text-gray-800"
                    style={{ wordBreak: 'break-word', whiteSpace: 'normal', lineHeight: '1.4' }}
                  >
                    {item.product_name}
                  </p>
                  {item.brand && (
                    <p className="text-xs text-gray-400 mt-0.5">{item.brand}</p>
                  )}
                </td>
                <td className="text-gray-500 text-xs" style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>
                  {item.quantity || '-'}
                </td>
                <td>
                  <span className={cn('font-bold whitespace-nowrap', item.is_cheapest ? 'text-green-700' : 'text-gray-800')}>
                    {formatBRL(item.price)}
                  </span>
                </td>
                <td className="whitespace-nowrap">
                  {item.difference != null && item.difference > 0 ? (
                    <span className="text-red-500 text-sm">
                      +{formatBRL(item.difference)}
                      {item.difference_pct != null && (
                        <span className="text-xs ml-1 text-red-400">({item.difference_pct.toFixed(1)}%)</span>
                      )}
                    </span>
                  ) : (
                    <span className="text-green-600 text-sm font-medium">Menor</span>
                  )}
                </td>
                <td>
                  {item.product_url ? (
                    <a href={item.product_url} target="_blank" rel="noopener noreferrer"
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

      {/* Bottom pagination */}
      <PaginationBar
        page={safePage}
        totalPages={totalPages}
        pageSize={pageSize}
        totalItems={sorted.length}
        onPageChange={setPage}
        onPageSizeChange={handlePageSize}
      />
    </div>
  )
}


function PaginationBar({
  page,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
}: {
  page: number
  totalPages: number
  pageSize: number
  totalItems: number
  onPageChange: (p: number) => void
  onPageSizeChange: (s: number) => void
}) {
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, totalItems)

  const pageButtons = useMemo(() => {
    const pages: (number | '...')[] = []
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
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
          <button
            key={size}
            onClick={() => onPageSizeChange(size)}
            className={cn(
              'px-2 py-0.5 rounded text-sm font-medium transition-colors',
              pageSize === size
                ? 'bg-brand-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            {size}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Primeira página"
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Página anterior"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {pageButtons.map((p, i) =>
          p === '...' ? (
            <span key={`dots-${i}`} className="px-1.5 text-gray-400 text-sm">...</span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={cn(
                'min-w-[32px] h-8 rounded text-sm font-medium transition-colors',
                page === p
                  ? 'bg-brand-600 text-white'
                  : 'hover:bg-gray-100 text-gray-700'
              )}
            >
              {p}
            </button>
          )
        )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Próxima página"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          title="Última página"
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
