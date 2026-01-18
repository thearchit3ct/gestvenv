<template>
  <div class="metrics-page">
    <header class="page-header">
      <div class="header-content">
        <h1>Tableau de bord</h1>
        <p class="subtitle">Métriques et statistiques d'utilisation</p>
      </div>
      <div class="header-actions">
        <select v-model="selectedPeriod" @change="refreshData" class="period-select">
          <option value="1h">Dernière heure</option>
          <option value="24h">24 heures</option>
          <option value="7d">7 jours</option>
          <option value="30d">30 jours</option>
        </select>
        <button @click="refreshData" class="btn btn-secondary" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          Actualiser
        </button>
      </div>
    </header>

    <div class="metrics-content">
      <!-- Cartes de résumé -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="card-icon environments">🐍</div>
          <div class="card-content">
            <span class="card-value">{{ stats.totalEnvironments }}</span>
            <span class="card-label">Environnements</span>
          </div>
          <div class="card-trend" :class="{ positive: stats.envTrend > 0 }">
            <span v-if="stats.envTrend !== 0">{{ stats.envTrend > 0 ? '+' : '' }}{{ stats.envTrend }}</span>
          </div>
        </div>

        <div class="summary-card">
          <div class="card-icon packages">📦</div>
          <div class="card-content">
            <span class="card-value">{{ stats.totalPackages }}</span>
            <span class="card-label">Packages installés</span>
          </div>
        </div>

        <div class="summary-card">
          <div class="card-icon storage">💾</div>
          <div class="card-content">
            <span class="card-value">{{ formatSize(stats.totalSize) }}</span>
            <span class="card-label">Espace utilisé</span>
          </div>
        </div>

        <div class="summary-card">
          <div class="card-icon cache">⚡</div>
          <div class="card-content">
            <span class="card-value">{{ stats.cacheHitRate }}%</span>
            <span class="card-label">Cache hit ratio</span>
          </div>
          <div class="card-progress">
            <div class="progress-bar" :style="{ width: stats.cacheHitRate + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Graphiques -->
      <div class="charts-grid">
        <div class="chart-container">
          <MetricsChart
            title="Temps de création (secondes)"
            type="line"
            :data="creationTimeData"
            unit="s"
            :loading="loading"
            @refresh="refreshData"
            @period-change="handlePeriodChange"
          />
        </div>

        <div class="chart-container">
          <MetricsChart
            title="Espace disque par environnement"
            type="bar"
            :data="diskUsageData"
            unit="MB"
            :loading="loading"
            :show-controls="false"
          />
        </div>

        <div class="chart-container">
          <MetricsChart
            title="Répartition des backends"
            type="donut"
            :data="backendData"
            :loading="loading"
            :show-controls="false"
          />
        </div>

        <div class="chart-container">
          <MetricsChart
            title="Activité récente"
            type="line"
            :data="activityData"
            unit="ops"
            :loading="loading"
            @refresh="refreshData"
          />
        </div>
      </div>

      <!-- Tableau d'historique -->
      <div class="history-section">
        <div class="section-header">
          <h2>Historique d'activité</h2>
          <div class="filter-controls">
            <select v-model="activityFilter" class="filter-select">
              <option value="all">Toutes les actions</option>
              <option value="create">Créations</option>
              <option value="delete">Suppressions</option>
              <option value="install">Installations</option>
              <option value="update">Mises à jour</option>
            </select>
          </div>
        </div>

        <div class="activity-table">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Action</th>
                <th>Environnement</th>
                <th>Détails</th>
                <th>Durée</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="activity in filteredActivities" :key="activity.id">
                <td>{{ formatDate(activity.timestamp) }}</td>
                <td>
                  <span class="action-badge" :class="activity.action">
                    {{ getActionLabel(activity.action) }}
                  </span>
                </td>
                <td>{{ activity.environment }}</td>
                <td>{{ activity.details }}</td>
                <td>{{ activity.duration }}ms</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!filteredActivities.length" class="no-activity">
          Aucune activité pour cette période
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import MetricsChart from '@/components/MetricsChart.vue'
import type { DataPoint } from '@/components/MetricsChart.vue'

interface Activity {
  id: string
  timestamp: Date
  action: 'create' | 'delete' | 'install' | 'update'
  environment: string
  details: string
  duration: number
}

interface Stats {
  totalEnvironments: number
  totalPackages: number
  totalSize: number
  cacheHitRate: number
  envTrend: number
}

const loading = ref(false)
const selectedPeriod = ref('24h')
const activityFilter = ref('all')

const stats = ref<Stats>({
  totalEnvironments: 0,
  totalPackages: 0,
  totalSize: 0,
  cacheHitRate: 0,
  envTrend: 0
})

const creationTimeData = ref<DataPoint[]>([])
const diskUsageData = ref<DataPoint[]>([])
const backendData = ref<DataPoint[]>([])
const activityData = ref<DataPoint[]>([])
const activities = ref<Activity[]>([])

const filteredActivities = computed(() => {
  if (activityFilter.value === 'all') {
    return activities.value
  }
  return activities.value.filter(a => a.action === activityFilter.value)
})

async function refreshData() {
  loading.value = true
  try {
    await Promise.all([
      loadStats(),
      loadChartData(),
      loadActivities()
    ])
  } catch (e) {
    console.error('Erreur chargement métriques:', e)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await fetch('/api/metrics/stats')
    if (response.ok) {
      stats.value = await response.json()
    } else {
      // Données de démo
      stats.value = {
        totalEnvironments: 12,
        totalPackages: 156,
        totalSize: 2.4 * 1024 * 1024 * 1024,
        cacheHitRate: 78,
        envTrend: 2
      }
    }
  } catch {
    // Données de démo
    stats.value = {
      totalEnvironments: 12,
      totalPackages: 156,
      totalSize: 2.4 * 1024 * 1024 * 1024,
      cacheHitRate: 78,
      envTrend: 2
    }
  }
}

async function loadChartData() {
  // Données de démo pour les graphiques
  creationTimeData.value = [
    { label: '00:00', value: 12.5 },
    { label: '04:00', value: 15.2 },
    { label: '08:00', value: 8.7 },
    { label: '12:00', value: 11.3 },
    { label: '16:00', value: 9.8 },
    { label: '20:00', value: 14.1 }
  ]

  diskUsageData.value = [
    { label: 'projet-api', value: 450, color: '#4a90d9' },
    { label: 'data-science', value: 820, color: '#10b981' },
    { label: 'web-app', value: 280, color: '#f59e0b' },
    { label: 'ml-training', value: 650, color: '#8b5cf6' },
    { label: 'testing', value: 120, color: '#ec4899' }
  ]

  backendData.value = [
    { label: 'UV', value: 8, color: '#4a90d9' },
    { label: 'Pip', value: 3, color: '#10b981' },
    { label: 'Poetry', value: 1, color: '#f59e0b' }
  ]

  activityData.value = [
    { label: 'Lun', value: 15 },
    { label: 'Mar', value: 23 },
    { label: 'Mer', value: 18 },
    { label: 'Jeu', value: 32 },
    { label: 'Ven', value: 28 },
    { label: 'Sam', value: 8 },
    { label: 'Dim', value: 5 }
  ]
}

async function loadActivities() {
  // Données de démo
  activities.value = [
    {
      id: '1',
      timestamp: new Date(Date.now() - 1000 * 60 * 5),
      action: 'create',
      environment: 'nouveau-projet',
      details: 'Python 3.12, UV backend',
      duration: 2340
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 1000 * 60 * 30),
      action: 'install',
      environment: 'projet-api',
      details: 'fastapi==0.104.1',
      duration: 890
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 1000 * 60 * 60),
      action: 'update',
      environment: 'data-science',
      details: 'numpy 1.25.0 → 1.26.0',
      duration: 1250
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 1000 * 60 * 120),
      action: 'delete',
      environment: 'test-env-old',
      details: 'Nettoyage environnement',
      duration: 450
    }
  ]
}

function handlePeriodChange(period: string) {
  selectedPeriod.value = period
  refreshData()
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
  }
  if (bytes >= 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }
  return (bytes / 1024).toFixed(1) + ' KB'
}

function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

function getActionLabel(action: string): string {
  const labels: Record<string, string> = {
    create: 'Création',
    delete: 'Suppression',
    install: 'Installation',
    update: 'Mise à jour'
  }
  return labels[action] || action
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.metrics-page {
  min-height: 100vh;
  background: var(--bg-secondary, #f8f9fa);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  background: var(--bg-primary, #fff);
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--text-secondary, #666);
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.period-select,
.filter-select {
  padding: 10px 16px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary {
  background: var(--bg-secondary, #f0f0f0);
  color: var(--text-primary, #333);
}

.btn-secondary:hover {
  background: var(--bg-hover, #e0e0e0);
}

.icon {
  width: 16px;
  height: 16px;
}

.metrics-content {
  padding: 24px 32px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.card-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 24px;
}

.card-icon.environments {
  background: rgba(74, 144, 217, 0.1);
}

.card-icon.packages {
  background: rgba(16, 185, 129, 0.1);
}

.card-icon.storage {
  background: rgba(245, 158, 11, 0.1);
}

.card-icon.cache {
  background: rgba(139, 92, 246, 0.1);
}

.card-content {
  flex: 1;
}

.card-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary, #333);
  line-height: 1.2;
}

.card-label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary, #666);
  margin-top: 4px;
}

.card-trend {
  padding: 4px 8px;
  background: var(--bg-secondary, #f0f0f0);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.card-trend.positive {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.card-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--bg-secondary, #f0f0f0);
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #a78bfa);
  border-radius: 0 2px 2px 0;
  transition: width 0.5s ease;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.chart-container {
  min-height: 300px;
}

.history-section {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  padding: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.activity-table {
  overflow-x: auto;
}

.activity-table table {
  width: 100%;
  border-collapse: collapse;
}

.activity-table th,
.activity-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.activity-table th {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.activity-table td {
  font-size: 14px;
  color: var(--text-primary, #333);
}

.action-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.action-badge.create {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.action-badge.delete {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.action-badge.install {
  background: rgba(74, 144, 217, 0.1);
  color: #4a90d9;
}

.action-badge.update {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.no-activity {
  padding: 32px;
  text-align: center;
  color: var(--text-secondary, #666);
}

/* Dark mode */
:global(.dark-mode) .metrics-page {
  background: var(--bg-secondary-dark, #111827);
}

:global(.dark-mode) .page-header {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .header-content h1,
:global(.dark-mode) .card-value,
:global(.dark-mode) .section-header h2 {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .subtitle,
:global(.dark-mode) .card-label {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .summary-card,
:global(.dark-mode) .history-section {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .period-select,
:global(.dark-mode) .filter-select {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .activity-table th {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .activity-table td {
  color: var(--text-primary-dark, #f9fafb);
  border-color: var(--border-color-dark, #374151);
}

@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
}
</style>
