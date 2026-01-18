<template>
  <div class="audit-log-page">
    <header class="page-header">
      <div class="header-content">
        <h1>Journal d'activité</h1>
        <p class="subtitle">Historique complet des opérations GestVenv</p>
      </div>
      <div class="header-actions">
        <button @click="exportLogs" class="btn btn-secondary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Exporter
        </button>
        <button @click="clearFilters" class="btn btn-secondary" v-if="hasFilters">
          Effacer filtres
        </button>
      </div>
    </header>

    <div class="audit-content">
      <!-- Filtres -->
      <div class="filters-bar">
        <div class="filter-group">
          <label>Période</label>
          <select v-model="filters.period" @change="loadLogs">
            <option value="1h">Dernière heure</option>
            <option value="24h">24 heures</option>
            <option value="7d">7 jours</option>
            <option value="30d">30 jours</option>
            <option value="all">Tout</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Action</label>
          <select v-model="filters.action" @change="loadLogs">
            <option value="">Toutes</option>
            <option value="create">Création</option>
            <option value="delete">Suppression</option>
            <option value="install">Installation</option>
            <option value="uninstall">Désinstallation</option>
            <option value="update">Mise à jour</option>
            <option value="activate">Activation</option>
            <option value="sync">Synchronisation</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Environnement</label>
          <select v-model="filters.environment" @change="loadLogs">
            <option value="">Tous</option>
            <option v-for="env in environments" :key="env" :value="env">
              {{ env }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <label>Statut</label>
          <select v-model="filters.status" @change="loadLogs">
            <option value="">Tous</option>
            <option value="success">Succès</option>
            <option value="error">Erreur</option>
            <option value="warning">Avertissement</option>
          </select>
        </div>

        <div class="filter-group search">
          <label>Rechercher</label>
          <input
            v-model="filters.search"
            type="search"
            placeholder="Rechercher..."
            @input="debouncedSearch"
          />
        </div>
      </div>

      <!-- Liste des logs -->
      <div class="logs-container" v-if="!loading">
        <div
          v-for="log in logs"
          :key="log.id"
          class="log-entry"
          :class="[log.status, { expanded: expandedLogs.has(log.id) }]"
        >
          <div class="log-header" @click="toggleExpand(log.id)">
            <div class="log-icon" :class="log.action">
              {{ getActionIcon(log.action) }}
            </div>

            <div class="log-info">
              <div class="log-title">
                <span class="action-label">{{ getActionLabel(log.action) }}</span>
                <span v-if="log.environment" class="env-name">{{ log.environment }}</span>
              </div>
              <div class="log-meta">
                <span class="timestamp">{{ formatDate(log.timestamp) }}</span>
                <span class="separator">•</span>
                <span class="duration">{{ log.duration }}ms</span>
                <span v-if="log.user" class="separator">•</span>
                <span v-if="log.user" class="user">{{ log.user }}</span>
              </div>
            </div>

            <div class="log-status">
              <span class="status-badge" :class="log.status">
                {{ getStatusLabel(log.status) }}
              </span>
            </div>

            <button class="expand-btn" :aria-label="expandedLogs.has(log.id) ? 'Réduire' : 'Développer'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>
          </div>

          <transition name="slide">
            <div v-if="expandedLogs.has(log.id)" class="log-details">
              <div class="detail-section" v-if="log.message">
                <h4>Message</h4>
                <p>{{ log.message }}</p>
              </div>

              <div class="detail-section" v-if="log.details">
                <h4>Détails</h4>
                <pre>{{ JSON.stringify(log.details, null, 2) }}</pre>
              </div>

              <div class="detail-section" v-if="log.stackTrace">
                <h4>Stack trace</h4>
                <pre class="error-trace">{{ log.stackTrace }}</pre>
              </div>

              <div class="detail-actions">
                <button @click="copyLog(log)" class="action-btn">
                  Copier
                </button>
                <button @click="viewRelated(log)" class="action-btn" v-if="log.relatedLogs?.length">
                  Voir {{ log.relatedLogs.length }} logs liés
                </button>
              </div>
            </div>
          </transition>
        </div>

        <div v-if="logs.length === 0" class="empty-state">
          <div class="empty-icon">📋</div>
          <h3>Aucun log trouvé</h3>
          <p>Aucune activité ne correspond à vos critères de recherche</p>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="page-btn"
          >
            Précédent
          </button>

          <div class="page-numbers">
            <button
              v-for="page in visiblePages"
              :key="page"
              @click="goToPage(page)"
              :class="{ active: page === currentPage }"
              class="page-number"
            >
              {{ page }}
            </button>
          </div>

          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="page-btn"
          >
            Suivant
          </button>
        </div>
      </div>

      <!-- Loading state -->
      <div v-else class="loading-state">
        <div class="spinner"></div>
        <p>Chargement des logs...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface LogEntry {
  id: string
  timestamp: Date
  action: string
  environment?: string
  status: 'success' | 'error' | 'warning'
  duration: number
  message?: string
  details?: Record<string, unknown>
  stackTrace?: string
  user?: string
  relatedLogs?: string[]
}

interface Filters {
  period: string
  action: string
  environment: string
  status: string
  search: string
}

const loading = ref(false)
const logs = ref<LogEntry[]>([])
const environments = ref<string[]>([])
const expandedLogs = ref<Set<string>>(new Set())
const currentPage = ref(1)
const totalPages = ref(1)
const perPage = 20

const filters = ref<Filters>({
  period: '24h',
  action: '',
  environment: '',
  status: '',
  search: ''
})

const hasFilters = computed(() => {
  return filters.value.action || filters.value.environment ||
         filters.value.status || filters.value.search ||
         filters.value.period !== '24h'
})

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, start + 4)
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

let searchTimeout: ReturnType<typeof setTimeout>

function debouncedSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    loadLogs()
  }, 300)
}

async function loadLogs() {
  loading.value = true
  try {
    // Simulation de chargement
    await new Promise(r => setTimeout(r, 500))

    // Données de démo
    logs.value = [
      {
        id: '1',
        timestamp: new Date(Date.now() - 1000 * 60 * 2),
        action: 'create',
        environment: 'nouveau-projet',
        status: 'success',
        duration: 2340,
        message: 'Environnement créé avec succès',
        details: {
          python_version: '3.12.1',
          backend: 'uv',
          packages_installed: 5
        }
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 1000 * 60 * 15),
        action: 'install',
        environment: 'projet-api',
        status: 'success',
        duration: 890,
        message: 'Package installé',
        details: {
          package: 'fastapi',
          version: '0.104.1',
          dependencies_installed: 12
        }
      },
      {
        id: '3',
        timestamp: new Date(Date.now() - 1000 * 60 * 45),
        action: 'sync',
        environment: 'data-science',
        status: 'warning',
        duration: 3200,
        message: 'Synchronisation terminée avec avertissements',
        details: {
          packages_updated: 3,
          packages_skipped: 1,
          warning: 'numpy version conflict resolved'
        }
      },
      {
        id: '4',
        timestamp: new Date(Date.now() - 1000 * 60 * 120),
        action: 'delete',
        environment: 'test-old',
        status: 'success',
        duration: 450,
        message: 'Environnement supprimé'
      },
      {
        id: '5',
        timestamp: new Date(Date.now() - 1000 * 60 * 180),
        action: 'update',
        environment: 'web-app',
        status: 'error',
        duration: 5600,
        message: 'Échec de la mise à jour',
        details: {
          package: 'tensorflow',
          from_version: '2.14.0',
          to_version: '2.15.0'
        },
        stackTrace: 'Error: CUDA version mismatch\n  at updatePackage (/app/manager.py:234)\n  at processUpdate (/app/cli.py:156)'
      }
    ]

    environments.value = ['nouveau-projet', 'projet-api', 'data-science', 'web-app', 'ml-training']
    totalPages.value = 3
  } catch (e) {
    console.error('Erreur chargement logs:', e)
  } finally {
    loading.value = false
  }
}

function toggleExpand(id: string) {
  if (expandedLogs.value.has(id)) {
    expandedLogs.value.delete(id)
  } else {
    expandedLogs.value.add(id)
  }
  expandedLogs.value = new Set(expandedLogs.value)
}

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadLogs()
  }
}

function clearFilters() {
  filters.value = {
    period: '24h',
    action: '',
    environment: '',
    status: '',
    search: ''
  }
  loadLogs()
}

function exportLogs() {
  const data = logs.value.map(log => ({
    timestamp: log.timestamp.toISOString(),
    action: log.action,
    environment: log.environment,
    status: log.status,
    message: log.message,
    duration: log.duration
  }))

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `gestvenv-logs-${new Date().toISOString().split('T')[0]}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function copyLog(log: LogEntry) {
  navigator.clipboard.writeText(JSON.stringify(log, null, 2))
}

function viewRelated(log: LogEntry) {
  console.log('View related logs:', log.relatedLogs)
}

function getActionIcon(action: string): string {
  const icons: Record<string, string> = {
    create: '🆕',
    delete: '🗑️',
    install: '📥',
    uninstall: '📤',
    update: '🔄',
    activate: '✅',
    sync: '🔁'
  }
  return icons[action] || '📋'
}

function getActionLabel(action: string): string {
  const labels: Record<string, string> = {
    create: 'Création',
    delete: 'Suppression',
    install: 'Installation',
    uninstall: 'Désinstallation',
    update: 'Mise à jour',
    activate: 'Activation',
    sync: 'Synchronisation'
  }
  return labels[action] || action
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    success: 'Succès',
    error: 'Erreur',
    warning: 'Avertissement'
  }
  return labels[status] || status
}

function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date)
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.audit-log-page {
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

.audit-content {
  padding: 24px 32px;
}

.filters-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  margin-bottom: 24px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group.search {
  flex: 1;
  min-width: 200px;
}

.filter-group label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-group select,
.filter-group input {
  padding: 10px 14px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-primary, #fff);
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: var(--primary-color, #4a90d9);
}

.logs-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-entry {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 12px;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.log-entry:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.log-entry.error {
  border-left: 4px solid #ef4444;
}

.log-entry.warning {
  border-left: 4px solid #f59e0b;
}

.log-entry.success {
  border-left: 4px solid #10b981;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  cursor: pointer;
}

.log-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-size: 20px;
  background: var(--bg-secondary, #f5f5f5);
}

.log-info {
  flex: 1;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.action-label {
  font-weight: 600;
  color: var(--text-primary, #333);
}

.env-name {
  padding: 2px 8px;
  background: var(--bg-secondary, #f0f0f0);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.log-meta {
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.separator {
  margin: 0 8px;
  opacity: 0.5;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.status-badge.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.status-badge.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.expand-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary, #666);
  cursor: pointer;
  transition: transform 0.2s ease;
}

.expand-btn:hover {
  background: var(--bg-secondary, #f5f5f5);
}

.expanded .expand-btn {
  transform: rotate(180deg);
}

.expand-btn svg {
  width: 18px;
  height: 18px;
}

.log-details {
  padding: 0 20px 20px;
  border-top: 1px solid var(--border-color, #e0e0e0);
  margin-top: 0;
  padding-top: 20px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-of-type {
  margin-bottom: 0;
}

.detail-section h4 {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-section pre {
  margin: 0;
  padding: 12px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 8px;
  font-size: 13px;
  overflow-x: auto;
}

.error-trace {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 6px;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
}

.action-btn:hover {
  background: var(--bg-secondary, #f5f5f5);
}

/* Animations */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: var(--text-primary, #333);
}

.empty-state p {
  color: var(--text-secondary, #666);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--primary-color, #4a90d9);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
}

.page-btn,
.page-number {
  padding: 8px 16px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  background: var(--bg-primary, #fff);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-number.active {
  background: var(--primary-color, #4a90d9);
  border-color: var(--primary-color, #4a90d9);
  color: white;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

/* Dark mode */
:global(.dark-mode) .audit-log-page {
  background: var(--bg-secondary-dark, #111827);
}

:global(.dark-mode) .page-header,
:global(.dark-mode) .filters-bar,
:global(.dark-mode) .log-entry {
  background: var(--bg-primary-dark, #1f2937);
  border-color: var(--border-color-dark, #374151);
}

:global(.dark-mode) .header-content h1,
:global(.dark-mode) .action-label {
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .subtitle,
:global(.dark-mode) .log-meta,
:global(.dark-mode) .filter-group label {
  color: var(--text-secondary-dark, #9ca3af);
}

:global(.dark-mode) .filter-group select,
:global(.dark-mode) .filter-group input {
  background: var(--bg-secondary-dark, #374151);
  border-color: var(--border-color-dark, #4b5563);
  color: var(--text-primary-dark, #f9fafb);
}

:global(.dark-mode) .detail-section pre {
  background: var(--bg-secondary-dark, #374151);
  color: var(--text-primary-dark, #f9fafb);
}

@media (max-width: 768px) {
  .filters-bar {
    flex-direction: column;
  }

  .filter-group {
    width: 100%;
  }

  .log-header {
    flex-wrap: wrap;
  }

  .log-status {
    order: -1;
    width: 100%;
    margin-bottom: 8px;
  }
}
</style>
