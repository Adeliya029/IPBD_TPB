import React from 'react'
import { FilterProvider, useFilter } from './context/FilterContext'
import Sidebar from './components/layout/Sidebar'
import InsightPanel from './components/layout/InsightPanel'
import FilterBar from './components/filter/FilterBar'
import HeroSection from './components/hero/HeroSection'
import KpiCards from './components/kpi/KpiCards'
import Top10Chart from './components/harga/Top10Chart'
import TrenHargaChart from './components/harga/TrenHargaChart'
import HeatmapTable from './components/harga/HeatmapTable'
import VolatilityChart from './components/harga/VolatilityChart'
import RankingProvinsi from './components/wilayah/RankingProvinsi'
import DetailTable from './components/wilayah/DetailTable'
import ScatterChart from './components/cuaca/ScatterChart'
import KorelasiCards from './components/cuaca/KorelasiCards'
import CuacaTable from './components/cuaca/CuacaTable'
import { PiePrediksi, PieCluster } from './components/ml/PieDistribusi'
import GaugeRisiko from './components/ml/GaugeRisiko'
import RankingKenaikan from './components/ml/RankingKenaikan'
import StackedBarPrediksi from './components/ml/StackedBarPrediksi'
import { apiScatterHujan, apiScatterSuhu } from './api'

function ScatterWithFilter({ title, apiFn }) {
  const { queryString } = useFilter()
  return <ScatterChart title={title} fetchFn={() => apiFn(queryString)} />
}

function SectionTitle({ id, title }) {
  const { activeSection } = useFilter()
  if (activeSection !== 'dashboard' && activeSection !== id) return null
  return (
    <div className="flex items-center gap-2 mt-8 mb-4">
      <div className="h-5 w-1 bg-primary rounded-full" />
      <h2 className="text-base font-semibold text-text-primary">{title}</h2>
    </div>
  )
}

function Section({ id, title, children }) {
  const { activeSection } = useFilter()
  if (activeSection !== 'dashboard' && activeSection !== id) return null
  return (
    <>
      <SectionTitle id={id} title={title} />
      {children}
    </>
  )
}

function DashboardContent() {
  return (
    <div id="main-content" className="flex-1 overflow-y-auto scrollbar-thin px-8 py-6">
      <div className="mb-5">
        <FilterBar />
      </div>
      <HeroSection />

      <Section id="dashboard" title="Ringkasan">
        <div className="mt-4">
          <KpiCards />
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Top10Chart />
          <TrenHargaChart />
        </div>
        <div className="mt-4">
          <GaugeRisiko />
        </div>
      </Section>

      <Section id="harga" title="Analisis Harga">
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Top10Chart />
          <TrenHargaChart />
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <HeatmapTable />
          <VolatilityChart />
        </div>
      </Section>

      <Section id="wilayah" title="Analisis Wilayah">
        <div className="grid grid-cols-2 gap-4 mt-4">
          <RankingProvinsi />
          <DetailTable />
        </div>
      </Section>

      <Section id="cuaca" title="Analisis Cuaca">
        <div className="grid grid-cols-2 gap-4 mt-4">
          <ScatterWithFilter title="🌧️ Scatter: Curah Hujan vs Harga" apiFn={apiScatterHujan} />
          <ScatterWithFilter title="🌡️ Scatter: Suhu vs Harga" apiFn={apiScatterSuhu} />
        </div>
        <div className="mt-4">
          <KorelasiCards />
        </div>
        <div className="mt-4">
          <CuacaTable />
        </div>
      </Section>

      <Section id="ml" title="Machine Learning & Risiko">
        <div className="grid grid-cols-3 gap-4 mt-4">
          <PiePrediksi />
          <PieCluster />
          <GaugeRisiko />
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <RankingKenaikan />
          <StackedBarPrediksi />
        </div>
      </Section>
    </div>
  )
}

export default function App() {
  return (
    <FilterProvider>
      <div className="flex h-screen bg-surface">
        <Sidebar />
        <DashboardContent />
        <InsightPanel />
      </div>
    </FilterProvider>
  )
}
