import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts'
import { useFilter } from '../../context/FilterContext'
import { apiTren } from '../../api'

const COLORS = ['#22C55E', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

export default function TrenHargaChart() {
  const { queryString } = useFilter()
  const [series, setSeries] = useState([])

  useEffect(() => {
    apiTren(queryString).then(s => setSeries(s)).catch(() => {})
  }, [queryString])

  if (series.length === 0) return null

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: p => p.map(s => `<div>${s.marker} ${s.seriesName}: <b>Rp${Number(s.value).toLocaleString('id-ID')}</b></div>`).join(''),
    },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    grid: { left: 60, right: 20, top: 10, bottom: 40 },
    xAxis: {
      type: 'time',
      axisLabel: { fontSize: 9, color: '#9CA3AF' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: v => `Rp${(v/1000).toFixed(0)}k`, fontSize: 9, color: '#9CA3AF' },
      splitLine: { lineStyle: { color: '#F3F4F6' } },
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: COLORS[i % COLORS.length] },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: COLORS[i % COLORS.length] + '20' },
        { offset: 1, color: COLORS[i % COLORS.length] + '00' },
      ]) },
      data: s.data,
    })),
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">📈 Tren Harga — Komoditas Utama</h3>
      <ReactEChartsCore option={option} style={{ height: 280 }} />
    </div>
  )
}
