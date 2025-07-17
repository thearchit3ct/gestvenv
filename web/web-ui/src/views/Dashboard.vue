<template>
  <div class="space-y-6">
    <!-- Header avec actions rapides -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Tableau de bord</h1>
        <p class="mt-2 text-gray-600">Vue d'ensemble de vos environnements virtuels Python</p>
      </div>
      
      <div class="flex space-x-3">
        <router-link
          to="/environments"
          class="btn-primary"
        >
          <PlusIcon class="h-4 w-4 mr-2" />
          Nouvel environnement
        </router-link>
      </div>
    </div>

    <!-- Statistiques générales -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Total environnements -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Environnements</p>
              <p class="text-3xl font-bold text-gray-900">{{ totalEnvironments }}</p>
            </div>
            <div class="p-3 bg-primary-100 rounded-full">
              <ServerIcon class="h-6 w-6 text-primary-600" />
            </div>
          </div>
        </div>
      </div>

      <!-- Environnement actif -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Actif</p>
              <p class="text-lg font-semibold text-gray-900 truncate">
                {{ activeEnvironment?.name || 'Aucun' }}
              </p>
            </div>
            <div class="p-3 bg-success-100 rounded-full">
              <CheckCircleIcon class="h-6 w-6 text-success-600" />
            </div>
          </div>
        </div>
      </div>

      <!-- Cache -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Cache</p>
              <p class="text-lg font-semibold text-gray-900">
                {{ systemStore.formatCacheSize() }}
              </p>
            </div>
            <div class="p-3 bg-warning-100 rounded-full">
              <CircleStackIcon class="h-6 w-6 text-warning-600" />
            </div>
          </div>
        </div>
      </div>

      <!-- Opérations en cours -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Opérations</p>
              <p class="text-3xl font-bold text-gray-900">{{ runningOperations.length }}</p>
            </div>
            <div class="p-3 bg-blue-100 rounded-full">
              <ClipboardDocumentListIcon class="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Grid principal -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <!-- Environnements récents -->
      <div class="xl:col-span-2 card">
        <div class="card-header">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900">Environnements récents</h3>
            <router-link
              to="/environments"
              class="text-sm text-primary-600 hover:text-primary-500"
            >
              Voir tout
            </router-link>
          </div>
        </div>
        <div class="card-body">
          <div v-if="environmentsLoading" class="flex justify-center py-8">
            <div class="loading"></div>
          </div>
          <div v-else-if="recentEnvironments.length === 0" class="text-center py-8 text-gray-500">
            <ServerIcon class="mx-auto h-12 w-12 text-gray-400" />
            <h3 class="mt-2 text-sm font-medium text-gray-900">Aucun environnement</h3>
            <p class="mt-1 text-sm text-gray-500">Commencez par créer votre premier environnement.</p>
            <div class="mt-6">
              <router-link to="/environments" class="btn-primary">
                <PlusIcon class="h-4 w-4 mr-2" />
                Créer un environnement
              </router-link>
            </div>
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="env in recentEnvironments"
              :key="env.name"
              class="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors duration-200"
            >
              <div class="flex items-center space-x-3">
                <div
                  class="w-3 h-3 rounded-full"
                  :class="getStatusColor(env.status)"
                ></div>
                <div>
                  <h4 class="font-medium text-gray-900">{{ env.name }}</h4>
                  <p class="text-sm text-gray-500">
                    {{ env.backend }} • {{ env.package_count }} packages • {{ formatSize(env.size_mb) }}
                  </p>
                </div>
              </div>
              <div class="flex items-center space-x-2">
                <span class="badge" :class="getStatusBadgeClass(env.status)">
                  {{ getStatusText(env.status) }}
                </span>
                <router-link
                  :to="`/environments/${env.name}`"
                  class="text-primary-600 hover:text-primary-500"
                >
                  <ArrowRightIcon class="h-4 w-4" />
                </router-link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar avec infos système et opérations -->
      <div class="space-y-6">
        <!-- Santé du système -->
        <div class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold text-gray-900">Santé du système</h3>
          </div>
          <div class="card-body">
            <div class="flex items-center justify-between mb-4">
              <span class="text-sm text-gray-600">État général</span>
              <span class="badge" :class="getHealthBadgeClass(systemHealth)">
                {{ getHealthText(systemHealth) }}
              </span>
            </div>
            
            <div v-if="systemInfo" class="space-y-3">
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Python</span>
                <span class="font-medium">{{ systemInfo.python_version }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">GestVenv</span>
                <span class="font-medium">{{ systemInfo.gestvenv_version }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Backends</span>
                <span class="font-medium">{{ systemInfo.backends_available.length }}</span>
              </div>
            </div>

            <div class="mt-4 pt-4 border-t border-gray-200">
              <button
                @click="runQuickDoctor"
                class="w-full btn-outline btn-sm"
                :disabled="runningDoctor"
              >
                <div v-if="runningDoctor" class="loading mr-2"></div>
                <HeartIcon v-else class="h-4 w-4 mr-2" />
                Diagnostic rapide
              </button>
            </div>
          </div>
        </div>

        <!-- Opérations récentes -->
        <div class="card">
          <div class="card-header">
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-semibold text-gray-900">Opérations récentes</h3>
              <router-link
                to="/operations"
                class="text-sm text-primary-600 hover:text-primary-500"
              >
                Voir tout
              </router-link>
            </div>
          </div>
          <div class="card-body">
            <div v-if="recentOperations.length === 0" class="text-center py-4 text-gray-500">
              <ClipboardDocumentListIcon class="mx-auto h-8 w-8 text-gray-400" />
              <p class="mt-2 text-sm">Aucune opération récente</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="operation in recentOperations.slice(0, 5)"
                :key="operation.id"
                class="flex items-center justify-between text-sm"
              >
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-gray-900 truncate">{{ operation.type }}</p>
                  <p class="text-gray-500 truncate">{{ operation.message || 'En cours...' }}</p>
                </div>
                <span class="badge badge-sm ml-2" :class="getOperationStatusClass(operation.status)">
                  {{ operation.status }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions rapides -->
        <div class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold text-gray-900">Actions rapides</h3>
          </div>
          <div class="card-body space-y-3">
            <router-link to="/templates" class="block w-full btn-outline btn-sm">
              <DocumentTextIcon class="h-4 w-4 mr-2" />
              Créer depuis template
            </router-link>
            <router-link to="/cache" class="block w-full btn-outline btn-sm">
              <CircleStackIcon class="h-4 w-4 mr-2" />
              Gérer le cache
            </router-link>
            <button
              @click="cleanupSystem"
              class="w-full btn-outline btn-sm"
              :disabled="runningCleanup"
            >
              <div v-if="runningCleanup" class="loading mr-2"></div>
              <TrashIcon v-else class="h-4 w-4 mr-2" />
              Nettoyer le système
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  PlusIcon,
  ServerIcon,
  CheckCircleIcon,
  CircleStackIcon,
  ClipboardDocumentListIcon,
  ArrowRightIcon,
  HeartIcon,
  DocumentTextIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

// Stores
import { useEnvironmentsStore } from '@/stores/environments'
import { useSystemStore } from '@/stores/system'

// State
const runningDoctor = ref(false)
const runningCleanup = ref(false)

// Stores
const environmentsStore = useEnvironmentsStore()
const systemStore = useSystemStore()

// Computed
const totalEnvironments = computed(() => environmentsStore.totalEnvironments)
const activeEnvironment = computed(() => environmentsStore.activeEnvironment)
const environmentsLoading = computed(() => environmentsStore.loading)
const systemInfo = computed(() => systemStore.systemInfo)
const systemHealth = computed(() => systemStore.systemHealth)
const runningOperations = computed(() => systemStore.runningOperations)
const recentOperations = computed(() => systemStore.recentOperations)

const recentEnvironments = computed(() => {
  return environmentsStore.filteredEnvironments
    .sort((a, b) => {
      const aTime = a.last_used ? new Date(a.last_used).getTime() : new Date(a.created_at).getTime()
      const bTime = b.last_used ? new Date(b.last_used).getTime() : new Date(b.created_at).getTime()
      return bTime - aTime
    })
    .slice(0, 5)
})

// Methods
function getStatusColor(status: string) {
  switch (status) {
    case 'healthy': return 'bg-green-400'
    case 'warning': return 'bg-yellow-400'
    case 'error': return 'bg-red-400'
    case 'creating': return 'bg-blue-400'
    default: return 'bg-gray-400'
  }
}

function getStatusBadgeClass(status: string) {
  switch (status) {
    case 'healthy': return 'badge-success'
    case 'warning': return 'badge-warning'
    case 'error': return 'badge-danger'
    case 'creating': return 'badge-primary'
    default: return 'badge-gray'
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'healthy': return 'Sain'
    case 'warning': return 'Attention'
    case 'error': return 'Erreur'
    case 'creating': return 'Création'
    default: return 'Inconnu'
  }
}

function getHealthBadgeClass(health: string) {
  switch (health) {
    case 'healthy': return 'badge-success'
    case 'warning': return 'badge-warning'
    case 'error': return 'badge-danger'
    default: return 'badge-gray'
  }
}

function getHealthText(health: string) {
  switch (health) {
    case 'healthy': return 'Excellent'
    case 'warning': return 'Attention'
    case 'error': return 'Problème'
    default: return 'Inconnu'
  }
}

function getOperationStatusClass(status: string) {
  switch (status) {
    case 'completed': return 'badge-success'
    case 'running': return 'badge-primary'
    case 'failed': return 'badge-danger'
    case 'cancelled': return 'badge-gray'
    default: return 'badge-warning'
  }
}

function formatSize(sizeMb: number) {
  if (sizeMb < 1024) {
    return `${sizeMb.toFixed(1)} MB`
  }
  return `${(sizeMb / 1024).toFixed(1)} GB`
}

async function runQuickDoctor() {
  runningDoctor.value = true
  try {
    await systemStore.runDoctor()
  } catch (error) {
    console.error('Failed to run doctor:', error)
  } finally {
    runningDoctor.value = false
  }
}

async function cleanupSystem() {
  runningCleanup.value = true
  try {
    await systemStore.cleanupSystem(true, false) // Orphelins seulement
  } catch (error) {
    console.error('Failed to cleanup system:', error)
  } finally {
    runningCleanup.value = false
  }
}

// Lifecycle
onMounted(async () => {
  // Initialiser les stores s'ils ne le sont pas déjà
  if (environmentsStore.totalEnvironments === 0) {
    environmentsStore.initialize()
  }
})
</script>