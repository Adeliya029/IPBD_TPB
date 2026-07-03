import React, { useState, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiInsights } from '../../api'
import { AlertTriangle, TrendingUp, Cloud, CheckCircle, Info } from 'lucide-react'

const ICON_MAP = {
  warning: TrendingUp,
  alert: AlertTriangle,
  info: Cloud,
  success: CheckCircle,
}

const COLOR_MAP = {
  warning: 'text-orange-600 bg-orange-50',
  alert: 'text-red-600 bg-red-50',
  info: 'text-blue-600 bg-blue-50',
  success: 'text-emerald-600 bg-emerald-50',
}

export default function InsightPanel() {
  const { queryString, activeSection } = useFilter()
  const [insights, setInsights] = useState([])

  useEffect(() => {
    apiInsights(queryString).then(setInsights).catch(() => setInsights([]))
  }, [queryString])

  const sectionTitles = {
    dashboard: 'Ringkasan Hari Ini',
    harga: 'Insight Harga',
    wilayah: 'Insight Wilayah',
    cuaca: 'Analisis Cuaca',
    ml: 'Ringkasan ML',
  }

  return (
    <aside className="w-[280px] h-screen bg-white border-l border-border flex flex-col shrink-0 overflow-y-auto scrollbar-thin">
      <div className="px-5 py-6 border-b border-border">
        <h2 className="font-semibold text-sm text-text-primary">{sectionTitles[activeSection] || 'Insight'}</h2>
      </div>
      <div className="flex-1 px-4 py-4 space-y-3">
        {insights.length === 0 && (
          <p className="text-xs text-text-muted text-center py-8">Memuat insight...</p>
        )}
        {insights.map((insight, i) => {
          const Icon = ICON_MAP[insight.type] || Info
          const colorClass = COLOR_MAP[insight.type] || 'text-gray-600 bg-gray-50'
          return (
            <div key={i} className={`p-4 rounded-xl ${colorClass}`}>
              <div className="flex items-start gap-2.5">
                <Icon size={16} className="shrink-0 mt-0.5" />
                <p className="text-xs leading-relaxed">{insight.emoji} {insight.text}</p>
              </div>
            </div>
          )
        })}
      </div>
      <div className="px-5 py-4 border-t border-border">
        <p className="text-[10px] text-text-muted">Data diperbarui otomatis setiap 1 menit</p>
      </div>
    </aside>
  )
}
