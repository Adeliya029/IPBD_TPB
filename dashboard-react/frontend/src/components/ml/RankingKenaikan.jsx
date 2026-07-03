import React, { useState, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiRankingKenaikan } from '../../api'

export default function RankingKenaikan() {
  const { queryString } = useFilter()
  const [data, setData] = useState([])

  useEffect(() => {
    apiRankingKenaikan(queryString).then(d => setData(d)).catch(() => {})
  }, [queryString])

  if (data.length === 0) return null

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">📈 Ranking Kenaikan Harga per Provinsi</h3>
      <div className="space-y-2.5">
        {data.map((row, i) => {
          const isUp = (row.avg_change || 0) >= 0
          return (
            <div key={row.provinsi} className="flex items-center justify-between text-xs">
              <span className="font-medium text-text-primary">{row.provinsi}</span>
              <span className={`font-semibold ${
                isUp ? 'text-red-500' : 'text-emerald-500'
              }`}>
                {isUp ? '+' : ''}{row.avg_change}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
