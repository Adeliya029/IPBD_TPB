import React, { useState, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiRankingProvinsi } from '../../api'

export default function RankingProvinsi() {
  const { queryString } = useFilter()
  const [data, setData] = useState([])

  useEffect(() => {
    apiRankingProvinsi(queryString).then(d => setData(d)).catch(() => {})
  }, [queryString])

  if (data.length === 0) return null

  const maxHarga = Math.max(...data.map(d => d.avg_harga), 1)

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">🏆 Ranking Provinsi</h3>
      <div className="space-y-3">
        {data.map((row, i) => (
          <div key={row.provinsi}>
            <div className="flex items-center justify-between text-xs mb-1">
              <div className="flex items-center gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  i === 0 ? 'bg-yellow-100 text-yellow-700' :
                  i === 1 ? 'bg-gray-100 text-gray-500' :
                  i === 2 ? 'bg-orange-50 text-orange-600' :
                  'bg-gray-50 text-gray-400'
                }`}>{i + 1}</span>
                <span className="font-medium text-text-primary">{row.provinsi}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-semibold text-text-primary">Rp{Number(row.avg_harga).toLocaleString('id-ID')}</span>
                <span className={`text-[10px] ${(row.avg_change || 0) >= 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                  {row.avg_change >= 0 ? '+' : ''}{row.avg_change}%
                </span>
              </div>
            </div>
            <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all" style={{
                width: `${(row.avg_harga / maxHarga) * 100}%`,
                background: `linear-gradient(90deg, #DCFCE7, ${row.avg_change >= 3 ? '#EF4444' : '#22C55E'})`,
              }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
