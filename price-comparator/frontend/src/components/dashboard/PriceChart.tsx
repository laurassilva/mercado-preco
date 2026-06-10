'use client'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import type { MarketSummary } from '@/types'
import { formatBRL } from '@/lib/utils'

interface Props {
  data: MarketSummary[]
}

const COLORS = ['#16a34a', '#2563eb', '#7c3aed', '#d97706', '#dc2626', '#0891b2', '#be185d']

export default function PriceChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        Sem dados para exibir
      </div>
    )
  }

  const chartData = [...data].sort((a, b) => a.avg_price - b.avg_price)

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="market_name" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => `R$${v}`} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: number) => [formatBRL(value), 'Preço Médio']}
          labelStyle={{ fontWeight: 600 }}
        />
        <Bar dataKey="avg_price" radius={[4, 4, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
