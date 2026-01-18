<template>
  <div class="metrics-chart" :class="{ 'loading': loading }">
    <div class="chart-header">
      <h3 class="chart-title">{{ title }}</h3>
      <div class="chart-controls" v-if="showControls">
        <select v-model="selectedPeriod" @change="onPeriodChange" aria-label="Période">
          <option value="1h">1 heure</option>
          <option value="24h">24 heures</option>
          <option value="7d">7 jours</option>
          <option value="30d">30 jours</option>
        </select>
        <button
          v-if="showRefresh"
          @click="$emit('refresh')"
          class="refresh-btn"
          :disabled="loading"
          aria-label="Actualiser"
        >
          <svg class="refresh-icon" :class="{ 'spinning': loading }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
    </div>

    <div v-else-if="error" class="error-state">
      <span>{{ error }}</span>
    </div>

    <div v-else class="chart-container">
      <!-- Bar Chart -->
      <template v-if="type === 'bar'">
        <div class="bar-chart" :style="{ height: chartHeight + 'px' }">
          <div class="y-axis">
            <span v-for="tick in yAxisTicks" :key="tick" class="y-tick">{{ formatValue(tick) }}</span>
          </div>
          <div class="bars">
            <div
              v-for="(item, index) in data"
              :key="index"
              class="bar-wrapper"
              @mouseenter="showTooltip(item, $event)"
              @mouseleave="hideTooltip"
            >
              <div
                class="bar"
                :style="{
                  height: getBarHeight(item.value) + '%',
                  backgroundColor: item.color || defaultColor
                }"
              ></div>
              <span class="bar-label">{{ item.label }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- Line Chart -->
      <template v-else-if="type === 'line'">
        <svg class="line-chart" :viewBox="`0 0 ${chartWidth} ${chartHeight}`" preserveAspectRatio="none">
          <defs>
            <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" :stop-color="defaultColor" stop-opacity="0.3" />
              <stop offset="100%" :stop-color="defaultColor" stop-opacity="0" />
            </linearGradient>
          </defs>

          <!-- Grid lines -->
          <g class="grid">
            <line
              v-for="tick in yAxisTicks"
              :key="tick"
              :x1="0"
              :y1="getYPosition(tick)"
              :x2="chartWidth"
              :y2="getYPosition(tick)"
              class="grid-line"
            />
          </g>

          <!-- Area -->
          <path :d="areaPath" :fill="`url(#${gradientId})`" />

          <!-- Line -->
          <path :d="linePath" :stroke="defaultColor" fill="none" stroke-width="2" />

          <!-- Points -->
          <g class="points">
            <circle
              v-for="(item, index) in data"
              :key="index"
              :cx="getXPosition(index)"
              :cy="getYPosition(item.value)"
              r="4"
              :fill="defaultColor"
              @mouseenter="showTooltip(item, $event)"
              @mouseleave="hideTooltip"
            />
          </g>
        </svg>
        <div class="x-axis">
          <span v-for="(item, index) in xAxisLabels" :key="index" class="x-tick">{{ item }}</span>
        </div>
      </template>

      <!-- Donut Chart -->
      <template v-else-if="type === 'donut'">
        <div class="donut-chart">
          <svg :viewBox="`0 0 ${donutSize} ${donutSize}`" class="donut-svg">
            <circle
              v-for="(segment, index) in donutSegments"
              :key="index"
              :cx="donutSize / 2"
              :cy="donutSize / 2"
              :r="donutRadius"
              fill="none"
              :stroke="segment.color"
              :stroke-width="donutStroke"
              :stroke-dasharray="segment.dashArray"
              :stroke-dashoffset="segment.dashOffset"
              class="donut-segment"
              @mouseenter="showTooltip(segment, $event)"
              @mouseleave="hideTooltip"
            />
          </svg>
          <div class="donut-center">
            <span class="donut-total">{{ formatValue(totalValue) }}</span>
            <span class="donut-label">Total</span>
          </div>
        </div>
        <div class="donut-legend">
          <div v-for="(item, index) in data" :key="index" class="legend-item">
            <span class="legend-color" :style="{ backgroundColor: item.color || getColor(index) }"></span>
            <span class="legend-label">{{ item.label }}</span>
            <span class="legend-value">{{ formatValue(item.value) }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- Tooltip -->
    <div
      v-if="tooltip.visible"
      class="tooltip"
      :style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }"
    >
      <strong>{{ tooltip.label }}</strong>
      <span>{{ formatValue(tooltip.value) }} {{ unit }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

export interface DataPoint {
  label: string
  value: number
  color?: string
}

interface Props {
  title: string
  type: 'bar' | 'line' | 'donut'
  data: DataPoint[]
  unit?: string
  loading?: boolean
  error?: string
  showControls?: boolean
  showRefresh?: boolean
  chartHeight?: number
  chartWidth?: number
}

const props = withDefaults(defineProps<Props>(), {
  unit: '',
  loading: false,
  error: '',
  showControls: true,
  showRefresh: true,
  chartHeight: 200,
  chartWidth: 400
})

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'period-change', period: string): void
}>()

const selectedPeriod = ref('24h')
const defaultColor = '#4a90d9'
const colors = ['#4a90d9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  label: '',
  value: 0
})

const gradientId = computed(() => `gradient-${Math.random().toString(36).substr(2, 9)}`)

const maxValue = computed(() => {
  if (!props.data.length) return 100
  return Math.max(...props.data.map(d => d.value)) * 1.1
})

const totalValue = computed(() => {
  return props.data.reduce((sum, d) => sum + d.value, 0)
})

const yAxisTicks = computed(() => {
  const max = maxValue.value
  const step = max / 4
  return [0, step, step * 2, step * 3, max].reverse()
})

const xAxisLabels = computed(() => {
  const step = Math.ceil(props.data.length / 6)
  return props.data
    .filter((_, i) => i % step === 0 || i === props.data.length - 1)
    .map(d => d.label)
})

// Donut chart calculations
const donutSize = 160
const donutRadius = 60
const donutStroke = 20
const circumference = 2 * Math.PI * donutRadius

const donutSegments = computed(() => {
  let offset = circumference / 4 // Start from top
  return props.data.map((item, index) => {
    const percentage = item.value / totalValue.value
    const dashArray = `${percentage * circumference} ${circumference}`
    const segment = {
      ...item,
      color: item.color || getColor(index),
      dashArray,
      dashOffset: -offset
    }
    offset += percentage * circumference
    return segment
  })
})

// Line chart path calculations
const linePath = computed(() => {
  if (!props.data.length) return ''
  return props.data
    .map((item, index) => {
      const x = getXPosition(index)
      const y = getYPosition(item.value)
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
})

const areaPath = computed(() => {
  if (!props.data.length) return ''
  const line = linePath.value
  const lastX = getXPosition(props.data.length - 1)
  const firstX = getXPosition(0)
  return `${line} L ${lastX} ${props.chartHeight} L ${firstX} ${props.chartHeight} Z`
})

function getColor(index: number): string {
  return colors[index % colors.length]
}

function getBarHeight(value: number): number {
  return (value / maxValue.value) * 100
}

function getXPosition(index: number): number {
  const padding = 20
  const available = props.chartWidth - padding * 2
  return padding + (index / (props.data.length - 1 || 1)) * available
}

function getYPosition(value: number): number {
  const padding = 10
  const available = props.chartHeight - padding * 2
  return padding + (1 - value / maxValue.value) * available
}

function formatValue(value: number): string {
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
  return value.toFixed(value % 1 === 0 ? 0 : 1)
}

function showTooltip(item: DataPoint, event: MouseEvent) {
  tooltip.value = {
    visible: true,
    x: event.clientX + 10,
    y: event.clientY - 30,
    label: item.label,
    value: item.value
  }
}

function hideTooltip() {
  tooltip.value.visible = false
}

function onPeriodChange() {
  emit('period-change', selectedPeriod.value)
}
</script>

<style scoped>
.metrics-chart {
  position: relative;
  padding: 16px;
  background: var(--bg-primary, #fff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #e0e0e0);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.chart-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.chart-controls select {
  padding: 6px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-primary, #fff);
}

.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  background: var(--bg-primary, #fff);
  cursor: pointer;
}

.refresh-btn:hover {
  background: var(--bg-hover, #f5f5f5);
}

.refresh-icon {
  width: 16px;
  height: 16px;
  color: var(--text-secondary, #666);
}

.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--primary-color, #4a90d9);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.error-state {
  padding: 24px;
  text-align: center;
  color: var(--error-color, #dc3545);
}

/* Bar Chart */
.bar-chart {
  display: flex;
  gap: 8px;
}

.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding-right: 8px;
  font-size: 11px;
  color: var(--text-secondary, #666);
}

.bars {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding-bottom: 24px;
  border-left: 1px solid var(--border-color, #e0e0e0);
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.bar {
  width: 100%;
  max-width: 40px;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
  cursor: pointer;
}

.bar:hover {
  opacity: 0.8;
}

.bar-label {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-secondary, #666);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 50px;
}

/* Line Chart */
.line-chart {
  width: 100%;
  height: 100%;
}

.grid-line {
  stroke: var(--border-color, #e0e0e0);
  stroke-dasharray: 4 4;
}

.points circle {
  cursor: pointer;
  transition: r 0.2s ease;
}

.points circle:hover {
  r: 6;
}

.x-axis {
  display: flex;
  justify-content: space-between;
  padding: 8px 20px 0;
  font-size: 11px;
  color: var(--text-secondary, #666);
}

/* Donut Chart */
.donut-chart {
  position: relative;
  width: 160px;
  height: 160px;
  margin: 0 auto;
}

.donut-svg {
  transform: rotate(-90deg);
}

.donut-segment {
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.donut-segment:hover {
  opacity: 0.8;
}

.donut-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.donut-total {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #333);
}

.donut-label {
  font-size: 12px;
  color: var(--text-secondary, #666);
}

.donut-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-label {
  color: var(--text-secondary, #666);
}

.legend-value {
  font-weight: 600;
  color: var(--text-primary, #333);
}

/* Tooltip */
.tooltip {
  position: fixed;
  z-index: 100;
  padding: 8px 12px;
  background: var(--bg-tooltip, #1f2937);
  color: white;
  border-radius: 6px;
  font-size: 13px;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Dark mode */
:global(.dark-mode) .metrics-chart {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .chart-title {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .chart-controls select,
:global(.dark-mode) .refresh-btn {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .loading-overlay {
  background: rgba(31, 41, 55, 0.8);
}

:global(.dark-mode) .y-axis,
:global(.dark-mode) .bar-label,
:global(.dark-mode) .x-axis,
:global(.dark-mode) .legend-label {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .donut-total,
:global(.dark-mode) .legend-value {
  color: var(--text-primary-dark, #f9fafb);
}
</style>
