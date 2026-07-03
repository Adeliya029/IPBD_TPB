const BASE = '/api'

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function apiKPI(qs) {
  return fetchJson(`${BASE}/kpi?${qs}`)
}
export function apiTop10(qs) {
  return fetchJson(`${BASE}/harga/top10?${qs}`)
}
export function apiTren(qs) {
  return fetchJson(`${BASE}/harga/tren?${qs}`)
}
export function apiHeatmap(qs) {
  return fetchJson(`${BASE}/harga/heatmap?${qs}`)
}
export function apiVolatilitas(qs) {
  return fetchJson(`${BASE}/harga/volatilitas?${qs}`)
}
export function apiRankingProvinsi(qs) {
  return fetchJson(`${BASE}/wilayah/ranking?${qs}`)
}
export function apiDetailKabKota(qs) {
  return fetchJson(`${BASE}/wilayah/detail?${qs}`)
}
export function apiScatterHujan(qs) {
  return fetchJson(`${BASE}/cuaca/scatter-hujan?${qs}`)
}
export function apiScatterSuhu(qs) {
  return fetchJson(`${BASE}/cuaca/scatter-suhu?${qs}`)
}
export function apiKorelasi(qs) {
  return fetchJson(`${BASE}/cuaca/korelasi?${qs}`)
}
export function apiCuacaRealtime() {
  return fetchJson(`${BASE}/cuaca/realtime`)
}
export function apiPrediksi() {
  return fetchJson(`${BASE}/ml/prediksi`)
}
export function apiCluster() {
  return fetchJson(`${BASE}/ml/cluster`)
}
export function apiRisiko() {
  return fetchJson(`${BASE}/ml/risiko`)
}
export function apiRankingKenaikan(qs) {
  return fetchJson(`${BASE}/ml/ranking-kenaikan?${qs}`)
}
export function apiPrediksiPerHari() {
  return fetchJson(`${BASE}/ml/prediksi-per-hari`)
}
export function apiInsights(qs) {
  return fetchJson(`${BASE}/insights?${qs}`)
}
