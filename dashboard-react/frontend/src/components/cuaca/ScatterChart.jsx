import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts'

const COLORS = ['#22C55E', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#06B6D4']

export default function ScatterChart({ title, fetchFn }) {
  const [data, setData] = useState([])

  useEffect(() => {
    fetchFn().then(d => setData(d)).catch(() => {})
  }, [])

  if (data.length === 0) return null

  const komMap = {}
  data.forEach(d => {
    if (!komMap[d.komoditas]) komMap[d.komoditas] = { name: d.komoditas, data: [] }
    komMap[d.komoditas].data.push([d.x, d.y])
  })
  const series = Object.values(komMap).slice(0, 8)

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: p => `${p.seriesName}<br/>X: <b>${Number(p.value[0]).toFixed(1)}</b><br/>Y: <b>Rp${Number(p.value[1]).toLocaleString('id-ID')}</b>`,
    },
    grid: { left: 60, right: 20, top: 10, bottom: 40 },
    xAxis: {
      type: 'value',
      name: title.includes('Hujan') ? 'Curah Hujan (mm)' : 'Suhu (°C)',
      nameTextStyle: { fontSize: 9, color: '#9CA3AF' },
      axisLabel: { fontSize: 9, color: '#9CA3AF' },
      splitLine: { lineStyle: { color: '#F3F4F6' } },
    },
    yAxis: {
      type: 'value',
      name: 'Harga (Rp)',
      nameTextStyle: { fontSize: 9, color: '#9CA3AF' },
      axisLabel: { formatter: v => `Rp${(v/1000).toFixed(0)}k`, fontSize: 9, color: '#9CA3AF' },
      splitLine: { lineStyle: { color: '#F3F4F6' } },
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'scatter',
      data: s.data,
      symbolSize: 4,
      itemStyle: { color: COLORS[i % COLORS.length], opacity: 0.6 },
    })),
    legend: {
      type: 'scroll',
      bottom: 0,
      textStyle: { fontSize: 9 },
      pageTextStyle: { fontSize: 9 },
    },
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">{title}</h3>
      <ReactEChartsCore option={option} style={{ height: 280 }} />
    </div>
  )
}
