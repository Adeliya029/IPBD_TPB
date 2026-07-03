import React, { useState, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiDetailKabKota } from '../../api'

export default function DetailTable() {
  const { queryString } = useFilter()
  const [data, setData] = useState([])

  useEffect(() => {
    apiDetailKabKota(queryString).then(d => setData(d)).catch(() => {})
  }, [queryString])

  if (data.length === 0) return null

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">📍 Detail Harga per Kab/Kota (Top 50)</h3>
      <div className="overflow-x-auto max-h-[320px] overflow-y-auto scrollbar-thin">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b border-border">
              <th className="text-left py-2 px-2 font-medium text-text-muted">Kab/Kota</th>
              <th className="text-left py-2 px-2 font-medium text-text-muted">Provinsi</th>
              <th className="text-left py-2 px-2 font-medium text-text-muted">Komoditas</th>
              <th className="text-right py-2 px-2 font-medium text-text-muted">Harga</th>
              <th className="text-right py-2 px-2 font-medium text-text-muted">Hari</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-border/50 hover:bg-gray-50/50">
                <td className="py-1.5 px-2 text-text-primary">{row.kab_kota}</td>
                <td className="py-1.5 px-2 text-text-muted">{row.provinsi}</td>
                <td className="py-1.5 px-2 text-text-primary">{row.komoditas}</td>
                <td className="py-1.5 px-2 text-right font-medium">
                  <span className={`px-2 py-0.5 rounded-lg ${
                    row.harga > 30000 ? 'bg-red-50 text-red-600' :
                    row.harga > 15000 ? 'bg-orange-50 text-orange-600' :
                    'bg-emerald-50 text-emerald-600'
                  }`}>
                    Rp{Number(row.harga).toLocaleString('id-ID')}
                  </span>
                </td>
                <td className="py-1.5 px-2 text-right text-text-muted">{row.hari}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
