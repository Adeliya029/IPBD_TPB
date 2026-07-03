import React, { useState, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiHeatmap } from '../../api'

function cellColor(val) {
  if (val === null || val === undefined) return 'bg-gray-50 text-gray-400'
  const n = Number(val)
  if (n > 3) return 'bg-red-100 text-red-700 font-medium'
  if (n > 1) return 'bg-orange-50 text-orange-600'
  if (n > -1) return 'bg-yellow-50 text-yellow-700'
  if (n > -3) return 'bg-emerald-50 text-emerald-600'
  return 'bg-green-100 text-green-700 font-medium'
}

export default function HeatmapTable() {
  const { queryString } = useFilter()
  const [data, setData] = useState([])

  useEffect(() => {
    apiHeatmap(queryString).then(d => setData(d)).catch(() => {})
  }, [queryString])

  if (data.length === 0) return null

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">📊 Heatmap Perubahan Harga per Bulan (%)</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 px-2 font-medium text-text-muted">Komoditas</th>
              {['Jan','Feb','Mar','Apr','Mei'].map(m => (
                <th key={m} className="text-center py-2 px-3 font-medium text-text-muted">{m}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.slice(0, 17).map(row => (
              <tr key={row.komoditas} className="border-b border-border/50 hover:bg-gray-50/50">
                <td className="py-2 px-2 text-text-primary font-medium whitespace-nowrap">{row.komoditas}</td>
                {['Jan','Feb','Mar','Apr','May'].map(m => (
                  <td key={m} className={`text-center py-2 px-3 rounded-lg ${cellColor(row[m])}`}>
                    {row[m] !== null ? `${row[m]}%` : '–'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
