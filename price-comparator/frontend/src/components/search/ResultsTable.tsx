'use client'
import { useState } from 'react'
import { ExternalLink, TrendingDown, TrendingUp, Award, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import type { ProductResult, SearchResponse } from '@/types'
import { formatBRL, formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'

type SortField = 'price' | 'market_name' | 'product_name' | 'difference'
type SortDir = 'asc' | 'desc'

interface Props {
  data: SearchResponse
  onExportPDF: () => void
  onExportExcel: () => void
  onExportCSV: () => void
}

export default function ResultsTable({ data, onExportPDF, onExportExcel, onExportCSV }: Props) {
  const [sort, setSort] = useState<{ field: SortField; dir: SortDir }>({ field: 'price', dir: 'asc' })

  const toggleSort = (field: SortField) => {
    setSort((prev) =>
      prev.field === field ? { field, dir: prev.dir === 'asc' ? 'desc' : 'asc' } : { field, dir: 'asc' }
    )
  }

  const sorted = [...data.results].sort((a, b) => {
    const va = sort.field === 'price' ? a.price
      : sort.field === 'difference' ? (a.difference ?? 0)
      : String(a[sort.field]).toLowerCase()
    const vb = sort.field === 'price' ? b.price
      : sort.field === 'difference' ? (b.difference ?? 0)
      : String(b[sort.field]).toLowerCase()
    if (va < vb) return sort.dir === 'asc' ? -1 : 1
    if (va > vb) return sort.dir === 'asc' ? 1 : -1
    return 0
  })

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

      {/* MOBILE: cards empilhados */}
      <div className="md:hidden space-y-3">
        {sorted.map((item, idx) => (
          <div
            key={idx}
            className={cn(
              'rounded-xl border p-4 space-y-2',
              item.is_cheapest
                ? 'bg-green-50 border-green-300'
                : 'bg-white border-gray-200'
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
                {item.is_cheapest && (
                  <span className="text-xs text-green-600 font-medium">✓ Mais barato</span>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>
                {item.difference != null && item.difference > 0
                  ? <span className="text-red-500">+{formatBRL(item.difference)} ({item.difference_pct?.toFixed(1)}%)</span>
                  : <span className="text-green-600">Menor preço</span>
                }
              </span>
              {item.product_url && (
                <a
                  href={item.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-brand-600 hover:text-brand-800 font-medium"
                >
                  Ver produto <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* DESKTOP: tabela */}
      <div className="hidden md:block table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th className="w-8">#</th>
              <th><SortBtn field="market_name" label="Mercado" /></th>
              <th><SortBtn field="product_name" label="Produto" /></th>
              <th>Marca</th>
              <th><SortBtn field="price" label="Preço" /></th>
              <th><SortBtn field="difference" label="Diferença" /></th>
              <th>Atualiz.</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, idx) => (
              <tr key={idx} className={cn(item.is_cheapest && 'cheapest')}>
                <td className="text-gray-400 text-xs">{idx + 1}</td>
                <td>
                  <div className="flex items-center gap-2 min-w-[120px]">
                    {item.is_cheapest && (
                      <span className="badge-green text-xs whitespace-nowrap">✓ Mais barato</span>
                    )}
                    <span className="font-medium text-gray-800 whitespace-nowrap">{item.market_name}</span>
                  </div>
                </td>
                <td className="max-w-[220px]">
                  <p className="truncate font-medium text-gray-800" title={item.product_name}>{item.product_name}</p>
                  {item.brand && <p className="text-xs text-gray-400">{item.brand}</p>}
                </td>
                <td className="text-gray-500 text-xs whitespace-nowrap">{item.quantity || '-'}</td>
                <td>
                  <span className={cn('font-bold', item.is_cheapest ? 'text-green-700' : 'text-gray-800')}>
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
                <td className="text-gray-400 text-xs whitespace-nowrap">{formatDate(item.last_updated)}</td>
                <td>
                  {item.product_url ? (
                    <a
                      href={item.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-800 font-medium whitespace-nowrap"
                    >
                      Ver produto <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
