<template>
  <div class="comparison-page">
    <header class="page-header">
      <div class="header-content">
        <h1>Comparer les environnements</h1>
        <p class="subtitle">Analysez les différences entre deux environnements</p>
      </div>
    </header>

    <div class="comparison-content">
      <!-- Sélecteurs d'environnements -->
      <div class="env-selectors">
        <div class="env-selector">
          <label>Environnement source</label>
          <select v-model="sourceEnv" @change="compare">
            <option value="">Sélectionner...</option>
            <option v-for="env in environments" :key="env.name" :value="env.name">
              {{ env.name }} (Python {{ env.python_version }})
            </option>
          </select>
        </div>

        <button @click="swapEnvironments" class="swap-btn" :disabled="!sourceEnv || !targetEnv" title="Inverser">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="17 1 21 5 17 9"></polyline>
            <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
            <polyline points="7 23 3 19 7 15"></polyline>
            <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
          </svg>
        </button>

        <div class="env-selector">
          <label>Environnement cible</label>
          <select v-model="targetEnv" @change="compare">
            <option value="">Sélectionner...</option>
            <option
              v-for="env in environments"
              :key="env.name"
              :value="env.name"
              :disabled="env.name === sourceEnv"
            >
              {{ env.name }} (Python {{ env.python_version }})
            </option>
          </select>
        </div>

        <button @click="compare" class="btn btn-primary" :disabled="!sourceEnv || !targetEnv || loading">
          <svg v-if="!loading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <span v-if="loading" class="spinner"></span>
          Comparer
        </button>
      </div>

      <!-- Résultats de comparaison -->
      <div v-if="comparisonResult" class="comparison-results">
        <!-- Résumé -->
        <div class="summary-section">
          <div class="summary-cards">
            <div class="summary-card only-source">
              <span class="card-value">{{ comparisonResult.onlyInSource.length }}</span>
              <span class="card-label">Uniquement dans {{ sourceEnv }}</span>
            </div>
            <div class="summary-card only-target">
              <span class="card-value">{{ comparisonResult.onlyInTarget.length }}</span>
              <span class="card-label">Uniquement dans {{ targetEnv }}</span>
            </div>
            <div class="summary-card different">
              <span class="card-value">{{ comparisonResult.different.length }}</span>
              <span class="card-label">Versions différentes</span>
            </div>
            <div class="summary-card same">
              <span class="card-value">{{ comparisonResult.same.length }}</span>
              <span class="card-label">Identiques</span>
            </div>
          </div>
        </div>

        <!-- Filtres -->
        <div class="results-filters">
          <button
            v-for="filter in filters"
            :key="filter.value"
            @click="activeFilter = filter.value"
            :class="{ active: activeFilter === filter.value }"
            class="filter-btn"
          >
            {{ filter.label }}
            <span class="count">{{ getFilterCount(filter.value) }}</span>
          </button>
        </div>

        <!-- Tableau de comparaison -->
        <div class="comparison-table">
          <table>
            <thead>
              <tr>
                <th>Package</th>
                <th>{{ sourceEnv }}</th>
                <th></th>
                <th>{{ targetEnv }}</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredResults" :key="item.package" :class="item.status">
                <td class="package-name">
                  <span class="name">{{ item.package }}</span>
                </td>
                <td class="version source">
                  <span v-if="item.sourceVersion" class="version-badge">
                    {{ item.sourceVersion }}
                  </span>
                  <span v-else class="not-installed">—</span>
                </td>
                <td class="arrow">
                  <svg v-if="item.status === 'different'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                  </svg>
                  <span v-else-if="item.status === 'only-source'" class="direction">→</span>
                  <span v-else-if="item.status === 'only-target'" class="direction">←</span>
                  <span v-else class="check">✓</span>
                </td>
                <td class="version target">
                  <span v-if="item.targetVersion" class="version-badge">
                    {{ item.targetVersion }}
                  </span>
                  <span v-else class="not-installed">—</span>
                </td>
                <td class="actions">
                  <button
                    v-if="item.status === 'only-source'"
                    @click="syncPackage(item.package, 'to-target')"
                    class="action-btn"
                    title="Installer dans la cible"
                  >
                    →
                  </button>
                  <button
                    v-if="item.status === 'only-target'"
                    @click="syncPackage(item.package, 'to-source')"
                    class="action-btn"
                    title="Installer dans la source"
                  >
                    ←
                  </button>
                  <button
                    v-if="item.status === 'different'"
                    @click="showVersionDialog(item)"
                    class="action-btn"
                    title="Synchroniser"
                  >
                    ⟷
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Actions globales -->
        <div class="global-actions">
          <button @click="exportComparison" class="btn btn-secondary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Exporter
          </button>
          <button @click="syncAll('to-target')" class="btn btn-primary" :disabled="!comparisonResult.onlyInSource.length">
            Synchroniser tout vers {{ targetEnv }}
          </button>
        </div>
      </div>

      <!-- État initial -->
      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>Sélectionnez deux environnements</h3>
        <p>Choisissez un environnement source et un environnement cible pour comparer leurs packages</p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Comparaison en cours...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Environment {
  name: string
  python_version: string
  packages: number
}

interface ComparisonItem {
  package: string
  sourceVersion: string | null
  targetVersion: string | null
  status: 'only-source' | 'only-target' | 'different' | 'same'
}

interface ComparisonResult {
  onlyInSource: ComparisonItem[]
  onlyInTarget: ComparisonItem[]
  different: ComparisonItem[]
  same: ComparisonItem[]
}

const environments = ref<Environment[]>([])
const sourceEnv = ref('')
const targetEnv = ref('')
const comparisonResult = ref<ComparisonResult | null>(null)
const loading = ref(false)
const activeFilter = ref('all')

const filters = [
  { value: 'all', label: 'Tous' },
  { value: 'only-source', label: 'Source uniquement' },
  { value: 'only-target', label: 'Cible uniquement' },
  { value: 'different', label: 'Différents' },
  { value: 'same', label: 'Identiques' }
]

const filteredResults = computed(() => {
  if (!comparisonResult.value) return []

  const allItems = [
    ...comparisonResult.value.onlyInSource,
    ...comparisonResult.value.onlyInTarget,
    ...comparisonResult.value.different,
    ...comparisonResult.value.same
  ]

  if (activeFilter.value === 'all') {
    return allItems.sort((a, b) => a.package.localeCompare(b.package))
  }

  return allItems
    .filter(item => item.status === activeFilter.value)
    .sort((a, b) => a.package.localeCompare(b.package))
})

function getFilterCount(filterValue: string): number {
  if (!comparisonResult.value) return 0

  switch (filterValue) {
    case 'all':
      return filteredResults.value.length
    case 'only-source':
      return comparisonResult.value.onlyInSource.length
    case 'only-target':
      return comparisonResult.value.onlyInTarget.length
    case 'different':
      return comparisonResult.value.different.length
    case 'same':
      return comparisonResult.value.same.length
    default:
      return 0
  }
}

async function loadEnvironments() {
  try {
    const response = await fetch('/api/environments')
    if (response.ok) {
      environments.value = await response.json()
    } else {
      // Données de démo
      environments.value = [
        { name: 'projet-api', python_version: '3.12.1', packages: 45 },
        { name: 'data-science', python_version: '3.11.7', packages: 78 },
        { name: 'web-app', python_version: '3.12.1', packages: 32 },
        { name: 'ml-training', python_version: '3.11.7', packages: 65 }
      ]
    }
  } catch {
    environments.value = [
      { name: 'projet-api', python_version: '3.12.1', packages: 45 },
      { name: 'data-science', python_version: '3.11.7', packages: 78 },
      { name: 'web-app', python_version: '3.12.1', packages: 32 },
      { name: 'ml-training', python_version: '3.11.7', packages: 65 }
    ]
  }
}

async function compare() {
  if (!sourceEnv.value || !targetEnv.value) return

  loading.value = true
  comparisonResult.value = null

  try {
    await new Promise(r => setTimeout(r, 800))

    // Données de démo
    comparisonResult.value = {
      onlyInSource: [
        { package: 'fastapi', sourceVersion: '0.104.1', targetVersion: null, status: 'only-source' },
        { package: 'uvicorn', sourceVersion: '0.24.0', targetVersion: null, status: 'only-source' },
        { package: 'pydantic', sourceVersion: '2.5.2', targetVersion: null, status: 'only-source' }
      ],
      onlyInTarget: [
        { package: 'numpy', sourceVersion: null, targetVersion: '1.26.2', status: 'only-target' },
        { package: 'pandas', sourceVersion: null, targetVersion: '2.1.3', status: 'only-target' },
        { package: 'scikit-learn', sourceVersion: null, targetVersion: '1.3.2', status: 'only-target' }
      ],
      different: [
        { package: 'requests', sourceVersion: '2.31.0', targetVersion: '2.28.2', status: 'different' },
        { package: 'pytest', sourceVersion: '7.4.3', targetVersion: '7.3.1', status: 'different' }
      ],
      same: [
        { package: 'click', sourceVersion: '8.1.7', targetVersion: '8.1.7', status: 'same' },
        { package: 'rich', sourceVersion: '13.7.0', targetVersion: '13.7.0', status: 'same' },
        { package: 'httpx', sourceVersion: '0.25.2', targetVersion: '0.25.2', status: 'same' }
      ]
    }
  } catch (e) {
    console.error('Erreur comparaison:', e)
  } finally {
    loading.value = false
  }
}

function swapEnvironments() {
  const temp = sourceEnv.value
  sourceEnv.value = targetEnv.value
  targetEnv.value = temp
  if (sourceEnv.value && targetEnv.value) {
    compare()
  }
}

function syncPackage(pkg: string, direction: 'to-source' | 'to-target') {
  console.log(`Sync ${pkg} ${direction}`)
  alert(`Synchronisation de ${pkg} ${direction === 'to-target' ? 'vers ' + targetEnv.value : 'vers ' + sourceEnv.value}`)
}

function showVersionDialog(item: ComparisonItem) {
  console.log('Show version dialog for:', item)
  alert(`Choisir la version pour ${item.package}:\n- ${sourceEnv.value}: ${item.sourceVersion}\n- ${targetEnv.value}: ${item.targetVersion}`)
}

function syncAll(direction: 'to-target' | 'to-source') {
  console.log(`Sync all ${direction}`)
  alert(`Synchronisation de tous les packages ${direction === 'to-target' ? 'vers ' + targetEnv.value : 'vers ' + sourceEnv.value}`)
}

function exportComparison() {
  if (!comparisonResult.value) return

  const data = {
    source: sourceEnv.value,
    target: targetEnv.value,
    comparison: comparisonResult.value,
    exportedAt: new Date().toISOString()
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `comparison-${sourceEnv.value}-vs-${targetEnv.value}.json`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  loadEnvironments()
})
</script>

<style scoped>
.comparison-page {
  min-height: 100vh;
  background: var(--bg-secondary, #f8f9fa);
}

.page-header {
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

.comparison-content {
  padding: 24px 32px;
}

.env-selectors {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 24px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  margin-bottom: 24px;
}

.env-selector {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.env-selector label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary, #666);
}

.env-selector select {
  padding: 12px 16px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
}

.swap-btn {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  background: var(--bg-secondary, #f5f5f5);
  cursor: pointer;
  color: var(--text-secondary, #666);
  transition: all 0.2s ease;
}

.swap-btn:hover:not(:disabled) {
  background: var(--bg-hover, #e8e8e8);
}

.swap-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.swap-btn svg {
  width: 20px;
  height: 20px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--primary-color, #4a90d9);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #3a7bc8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.summary-section {
  margin-bottom: 24px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-card {
  padding: 20px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  text-align: center;
}

.summary-card.only-source {
  border-left: 4px solid #4a90d9;
}

.summary-card.only-target {
  border-left: 4px solid #10b981;
}

.summary-card.different {
  border-left: 4px solid #f59e0b;
}

.summary-card.same {
  border-left: 4px solid #8b5cf6;
}

.card-value {
  display: block;
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary, #333);
}

.card-label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary, #666);
  margin-top: 4px;
}

.results-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 20px;
  background: var(--bg-primary, #fff);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.filter-btn.active {
  background: var(--primary-color, #4a90d9);
  border-color: var(--primary-color, #4a90d9);
  color: white;
}

.filter-btn .count {
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  font-size: 12px;
}

.filter-btn.active .count {
  background: rgba(255, 255, 255, 0.2);
}

.comparison-table {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
}

.comparison-table table {
  width: 100%;
  border-collapse: collapse;
}

.comparison-table th,
.comparison-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.comparison-table th {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-secondary, #f8f9fa);
}

.comparison-table tbody tr:last-child td {
  border-bottom: none;
}

.comparison-table tbody tr.only-source {
  background: rgba(74, 144, 217, 0.05);
}

.comparison-table tbody tr.only-target {
  background: rgba(16, 185, 129, 0.05);
}

.comparison-table tbody tr.different {
  background: rgba(245, 158, 11, 0.05);
}

.package-name .name {
  font-weight: 500;
  color: var(--text-primary, #333);
}

.version-badge {
  display: inline-block;
  padding: 4px 10px;
  background: var(--bg-secondary, #f0f0f0);
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
}

.not-installed {
  color: var(--text-secondary, #999);
}

.arrow {
  text-align: center;
  width: 50px;
}

.arrow svg {
  width: 20px;
  height: 20px;
  color: var(--text-secondary, #666);
}

.direction {
  font-size: 18px;
  color: var(--text-secondary, #666);
}

.check {
  color: #10b981;
  font-size: 16px;
}

.actions {
  width: 80px;
}

.action-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  background: var(--bg-primary, #fff);
  cursor: pointer;
  font-size: 14px;
}

.action-btn:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.global-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.empty-state,
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 40px;
  text-align: center;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px;
  font-size: 20px;
  color: var(--text-primary, #333);
}

.empty-state p {
  margin: 0;
  color: var(--text-secondary, #666);
}

.loading-state .spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--primary-color, #4a90d9);
  margin-bottom: 16px;
}

/* Dark mode */
:global(.dark-mode) .comparison-page {
  background: var(--bg-secondary-dark, #111827);
}

:global(.dark-mode) .page-header,
:global(.dark-mode) .env-selectors,
:global(.dark-mode) .summary-card,
:global(.dark-mode) .comparison-table,
:global(.dark-mode) .filter-btn:not(.active) {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .header-content h1,
:global(.dark-mode) .card-value,
:global(.dark-mode) .package-name .name {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .subtitle,
:global(.dark-mode) .card-label,
:global(.dark-mode) .env-selector label {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .env-selector select {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .comparison-table th {
  background: var(--bg-secondary-dark, #374151);
}

@media (max-width: 1024px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .env-selectors {
    flex-direction: column;
    align-items: stretch;
  }

  .swap-btn {
    align-self: center;
    transform: rotate(90deg);
  }

  .summary-cards {
    grid-template-columns: 1fr;
  }

  .results-filters {
    flex-wrap: wrap;
  }
}
</style>
