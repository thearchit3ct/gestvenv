<template>
  <div class="dependency-graph-page">
    <header class="page-header">
      <div class="header-content">
        <h1>Graphe des dépendances</h1>
        <p class="subtitle">Visualisez les relations entre les packages de vos environnements</p>
      </div>
      <div class="header-actions">
        <select v-model="selectedEnvironment" @change="loadDependencies" class="env-select">
          <option value="">Sélectionner un environnement</option>
          <option v-for="env in environments" :key="env.name" :value="env.name">
            {{ env.name }}
          </option>
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

    <div class="content-grid">
      <!-- Panneau latéral avec l'arbre -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>Structure</h2>
          <div class="view-toggle">
            <button
              @click="viewMode = 'tree'"
              :class="{ active: viewMode === 'tree' }"
              title="Vue arbre"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
              </svg>
            </button>
            <button
              @click="viewMode = 'graph'"
              :class="{ active: viewMode === 'graph' }"
              title="Vue graphe"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <circle cx="19" cy="5" r="2"></circle>
                <circle cx="5" cy="5" r="2"></circle>
                <circle cx="19" cy="19" r="2"></circle>
                <circle cx="5" cy="19" r="2"></circle>
                <line x1="12" y1="9" x2="12" y2="5"></line>
                <line x1="14.5" y1="10.5" x2="17" y2="7"></line>
                <line x1="9.5" y1="10.5" x2="7" y2="7"></line>
              </svg>
            </button>
          </div>
        </div>

        <DependencyTree
          v-if="viewMode === 'tree'"
          :dependencies="dependencies"
          :loading="loading"
          :error="error"
          @select="selectPackage"
          @retry="loadDependencies"
        />

        <div v-else class="graph-placeholder">
          <p>Vue graphe D3.js</p>
          <small>(À implémenter)</small>
        </div>
      </aside>

      <!-- Panneau principal -->
      <main class="main-content">
        <div v-if="!selectedEnvironment" class="empty-state">
          <div class="empty-icon">📦</div>
          <h3>Sélectionnez un environnement</h3>
          <p>Choisissez un environnement dans la liste pour visualiser ses dépendances</p>
        </div>

        <div v-else-if="selectedPackage" class="package-details">
          <div class="detail-header">
            <h2>{{ selectedPackage.name }}</h2>
            <span class="version-badge">{{ selectedPackage.version }}</span>
          </div>

          <div class="detail-grid">
            <div class="detail-card">
              <h4>Informations</h4>
              <dl>
                <div class="info-row">
                  <dt>Version</dt>
                  <dd>{{ selectedPackage.version }}</dd>
                </div>
                <div v-if="selectedPackage.license" class="info-row">
                  <dt>Licence</dt>
                  <dd>{{ selectedPackage.license }}</dd>
                </div>
                <div v-if="selectedPackage.is_dev" class="info-row">
                  <dt>Type</dt>
                  <dd><span class="dev-badge">Dépendance dev</span></dd>
                </div>
              </dl>
            </div>

            <div class="detail-card">
              <h4>Dépendances directes</h4>
              <ul v-if="selectedPackage.dependencies?.length" class="dep-list">
                <li v-for="dep in selectedPackage.dependencies" :key="dep.name" @click="selectPackage(dep)">
                  <span class="dep-name">{{ dep.name }}</span>
                  <span class="dep-version">{{ dep.version }}</span>
                </li>
              </ul>
              <p v-else class="no-deps">Aucune dépendance</p>
            </div>

            <div class="detail-card">
              <h4>Actions</h4>
              <div class="action-buttons">
                <a
                  :href="`https://pypi.org/project/${selectedPackage.name}/`"
                  target="_blank"
                  rel="noopener"
                  class="btn btn-outline"
                >
                  Voir sur PyPI
                </a>
                <button @click="showUpgradeInfo" class="btn btn-outline">
                  Vérifier les mises à jour
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="select-package-hint">
          <div class="hint-icon">👆</div>
          <p>Cliquez sur un package dans l'arbre pour voir ses détails</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DependencyTree from '@/components/DependencyTree.vue'
import type { Dependency } from '@/components/DependencyTree.vue'

interface Environment {
  name: string
  python_version: string
  packages: number
}

const environments = ref<Environment[]>([])
const selectedEnvironment = ref('')
const dependencies = ref<Dependency[]>([])
const selectedPackage = ref<Dependency | null>(null)
const loading = ref(false)
const error = ref('')
const viewMode = ref<'tree' | 'graph'>('tree')

async function loadEnvironments() {
  try {
    const response = await fetch('/api/environments')
    if (response.ok) {
      environments.value = await response.json()
    }
  } catch (e) {
    console.error('Erreur chargement environnements:', e)
  }
}

async function loadDependencies() {
  if (!selectedEnvironment.value) {
    dependencies.value = []
    return
  }

  loading.value = true
  error.value = ''
  selectedPackage.value = null

  try {
    const response = await fetch(`/api/environments/${selectedEnvironment.value}/dependencies`)
    if (response.ok) {
      dependencies.value = await response.json()
    } else {
      throw new Error('Erreur lors du chargement')
    }
  } catch (e) {
    error.value = 'Impossible de charger les dépendances'
    console.error(e)
  } finally {
    loading.value = false
  }
}

function refreshData() {
  loadDependencies()
}

function selectPackage(pkg: Dependency) {
  selectedPackage.value = pkg
}

function showUpgradeInfo() {
  // À implémenter: vérification des mises à jour
  alert('Fonctionnalité à venir')
}

onMounted(() => {
  loadEnvironments()
})
</script>

<style scoped>
.dependency-graph-page {
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

.env-select {
  padding: 10px 16px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  font-size: 14px;
  min-width: 200px;
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

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color, #e0e0e0);
  color: var(--text-primary, #333);
}

.btn-outline:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon {
  width: 16px;
  height: 16px;
}

.content-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 0;
  min-height: calc(100vh - 100px);
}

.sidebar {
  background: var(--bg-primary, #fff);
  border-right: 1px solid var(--border-color, #e0e0e0);
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.sidebar-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.view-toggle {
  display: flex;
  gap: 4px;
}

.view-toggle button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  color: var(--text-secondary, #666);
}

.view-toggle button:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.view-toggle button.active {
  background: var(--primary-color, #4a90d9);
  border-color: var(--primary-color, #4a90d9);
  color: white;
}

.view-toggle button svg {
  width: 16px;
  height: 16px;
}

.graph-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--text-secondary, #666);
}

.main-content {
  padding: 24px;
}

.empty-state,
.select-package-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-secondary, #666);
}

.empty-icon,
.hint-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: var(--text-primary, #333);
}

.package-details {
  max-width: 800px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.detail-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.version-badge {
  padding: 4px 12px;
  background: var(--primary-color, #4a90d9);
  color: white;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
}

.detail-grid {
  display: grid;
  gap: 16px;
}

.detail-card {
  padding: 20px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
}

.detail-card h4 {
  margin: 0 0 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color, #f0f0f0);
}

.info-row:last-child {
  border-bottom: none;
}

.info-row dt {
  color: var(--text-secondary, #666);
}

.info-row dd {
  margin: 0;
  font-weight: 500;
  color: var(--text-primary, #333);
}

.dev-badge {
  padding: 2px 8px;
  background: var(--info-color, #3b82f6);
  color: white;
  border-radius: 4px;
  font-size: 12px;
}

.dep-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.dep-list li {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.dep-list li:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.dep-name {
  font-weight: 500;
}

.dep-version {
  color: var(--text-secondary, #666);
  font-size: 13px;
}

.no-deps {
  color: var(--text-secondary, #666);
  font-style: italic;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* Dark mode */
:global(.dark-mode) .dependency-graph-page {
  background: var(--bg-secondary-dark, #111827);
}

:global(.dark-mode) .page-header {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .header-content h1 {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .subtitle {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .env-select {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .sidebar {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .detail-card {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .detail-header h2,
:global(.dark-mode) .info-row dd,
:global(.dark-mode) .dep-name {
  color: var(--text-primary-dark, #f9fafb);
}

@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .sidebar {
    max-height: 400px;
    border-right: none;
    border-bottom: 1px solid var(--border-color, #e0e0e0);
  }
}
</style>
