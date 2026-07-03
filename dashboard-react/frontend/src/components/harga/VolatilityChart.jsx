import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts'
import { useFilter } from '../../context/FilterContext'
import { apiVolatilitas } from '../../api'

export default function VolatilityChart() {
  const { queryString } = useFilter()
  const [data, setData] = useState([])

  useEffect(() => {
    apiVolatilitas(queryString).then(d => setData(d.slice(0, 10))).catch(() => {})
  }, [queryString])

  if (data.length === 0) return null

  const maxVal = Math.max(...data.map(d => d.value))
  const names = data.map(d => d.komoditas).reverse()
  const values = data.map(d => d.value).reverse()

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}: <b>Rp${Number(p[0].value).toLocaleString('id-ID')}</b>`,
    },
    grid: { left: 140, right: 40, top: 10, bottom: 10 },
    xAxis: { type: 'value', axisLabel: { formatter: v => `Rp${(v/1000).toFixed(0)}k`, fontSize: 9 }, splitLine: { lineStyle: { color: '#F3F4F6' } } },
    yAxis: { type: 'category', data: names, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar',
      data: values.map(v => ({
        value: v,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: v / maxVal, color: '#FEF3C7' },
            { offset: 1, color: '#F59E0B' },
          ]),
          borderRadius: [0, 6, 6, 0],
        },
      })),
      barWidth: 16,
    }],
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">📉 Volatilitas Harga (Top 10)</h3>
      <ReactEChartsCore option={option} style={{ height: 240 }} />
    </div>
  )
}
