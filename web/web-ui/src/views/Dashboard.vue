<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <!-- Header principal avec gradient -->
    <div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white">
      <div class="container mx-auto px-6 py-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-4xl font-bold mb-2">Bienvenue sur GestVenv</h1>
            <p class="text-blue-100 text-lg">Gestionnaire intelligent d'environnements virtuels Python</p>
            <div class="flex items-center mt-4 space-x-6">
              <div class="flex items-center space-x-2">
                <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span class="text-sm text-blue-100">Système opérationnel</span>
              </div>
              <div class="text-sm text-blue-100">
                Dernière activité: {{ formatLastActivity() }}
              </div>
            </div>
          </div>
          
          <div class="hidden md:flex space-x-4">
            <router-link
              to="/environments"
              class="bg-white/10 backdrop-blur-sm border border-white/20 text-white px-6 py-3 rounded-lg hover:bg-white/20 transition-all duration-200 flex items-center space-x-2"
            >
              <PlusIcon class="h-5 w-5" />
              <span>Nouvel environnement</span>
            </router-link>
            <router-link
              to="/templates"
              class="bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600 transition-all duration-200 flex items-center space-x-2"
            >
              <SparklesIcon class="h-5 w-5" />
              <span>Depuis template</span>
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <div class="container mx-auto px-6 py-8">
      <!-- Métriques principales avec design amélioré -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 -mt-12 mb-8">
        <!-- Total environnements -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div class="p-6">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600 mb-1">Environnements</p>
                <p class="text-3xl font-bold text-gray-900">{{ totalEnvironments }}</p>
                <p class="text-xs text-green-600 mt-1 flex items-center">
                  <ArrowUpIcon class="h-3 w-3 mr-1" />
                  {{ healthyEnvironments }} sains
                </p>
              </div>
              <div class="p-4 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg">
                <ServerIcon class="h-8 w-8 text-white" />
              </div>
            </div>
          </div>
          <div class="h-1 bg-gradient-to-r from-blue-500 to-blue-600"></div>
        </div>

        <!-- Environnement actif -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div class="p-6">
            <div class="flex items-center justify-between">
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium text-gray-600 mb-1">Environnement actif</p>
                <p class="text-lg font-bold text-gray-900 truncate">
                  {{ activeEnvironment?.name || 'Aucun' }}
                </p>
                <p class="text-xs text-gray-500 mt-1" v-if="activeEnvironment">
                  {{ activeEnvironment.package_count }} packages
                </p>
              </div>
              <div class="p-4 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex-shrink-0">
                <CheckCircleIcon class="h-8 w-8 text-white" />
              </div>
            </div>
          </div>
          <div class="h-1 bg-gradient-to-r from-green-500 to-green-600"></div>
        </div>

        <!-- Cache intelligent -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div class="p-6">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600 mb-1">Cache</p>
                <p class="text-xl font-bold text-gray-900">
                  {{ formatCacheSize() }}
                </p>
                <p class="text-xs text-orange-600 mt-1 flex items-center">
                  <SparklesIcon class="h-3 w-3 mr-1" />
                  {{ cacheHitRate }}% efficacité
                </p>
              </div>
              <div class="p-4 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg">
                <CircleStackIcon class="h-8 w-8 text-white" />
              </div>
            </div>
          </div>
          <div class="h-1 bg-gradient-to-r from-orange-500 to-orange-600"></div>
        </div>

        <!-- Activité système -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div class="p-6">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600 mb-1">Activité</p>
                <p class="text-3xl font-bold text-gray-900">{{ runningOperations.length }}</p>
                <p class="text-xs text-purple-600 mt-1 flex items-center">
                  <ClockIcon class="h-3 w-3 mr-1" />
                  {{ completedToday }} aujourd'hui
                </p>
              </div>
              <div class="p-4 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg">
                <CogIcon class="h-8 w-8 text-white" />
              </div>
            </div>
          </div>
          <div class="h-1 bg-gradient-to-r from-purple-500 to-purple-600"></div>
        </div>
      </div>

      <!-- Contenu principal avec layout amélioré -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <!-- Section principale: Environnements -->
        <div class="xl:col-span-2 space-y-6">
          <!-- Environnements récents avec design moderne -->
          <div class="bg-white rounded-xl shadow-lg border border-gray-200">
            <div class="p-6 border-b border-gray-200">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-xl font-semibold text-gray-900">Environnements récents</h3>
                  <p class="text-sm text-gray-500 mt-1">Vos 5 derniers environnements utilisés</p>
                </div>
                <router-link
                  to="/environments"
                  class="text-blue-600 hover:text-blue-700 font-medium text-sm flex items-center space-x-1 transition-colors"
                >
                  <span>Voir tout</span>
                  <ArrowRightIcon class="h-4 w-4" />
                </router-link>
              </div>
            </div>
            
            <div class="p-6">
              <div v-if="environmentsLoading" class="flex justify-center py-12">
                <div class="flex items-center space-x-3">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <span class="text-gray-600">Chargement des environnements...</span>
                </div>
              </div>
              
              <div v-else-if="recentEnvironments.length === 0" class="text-center py-12">
                <div class="bg-gray-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-4">
                  <ServerIcon class="h-10 w-10 text-gray-400" />
                </div>
                <h3 class="text-lg font-medium text-gray-900 mb-2">Aucun environnement</h3>
                <p class="text-gray-500 mb-6">Créez votre premier environnement virtuel pour commencer.</p>
                <div class="flex flex-col sm:flex-row gap-3 justify-center">
                  <router-link to="/environments" class="btn btn-primary">
                    <PlusIcon class="h-4 w-4 mr-2" />
                    Créer un environnement
                  </router-link>
                  <router-link to="/templates" class="btn btn-outline">
                    <SparklesIcon class="h-4 w-4 mr-2" />
                    Depuis un template
                  </router-link>
                </div>
              </div>
              
              <div v-else class="space-y-3">
                <div
                  v-for="env in recentEnvironments"
                  :key="env.name"
                  class="group flex items-center justify-between p-4 border-2 border-gray-100 rounded-lg hover:border-blue-200 hover:bg-blue-50/50 transition-all duration-200 cursor-pointer"
                  @click="$router.push(`/environments/${env.name}`)"
                >
                  <div class="flex items-center space-x-4">
                    <div class="relative">
                      <div
                        class="w-12 h-12 rounded-lg flex items-center justify-center"
                        :class="getEnvironmentBgColor(env.backend)"
                      >
                        <component :is="getBackendIcon(env.backend)" class="h-6 w-6 text-white" />
                      </div>
                      <div
                        class="absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-white"
                        :class="getStatusColor(env.status)"
                      ></div>
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="flex items-center space-x-2">
                        <h4 class="font-semibold text-gray-900 truncate">{{ env.name }}</h4>
                        <span v-if="env.active" class="badge badge-primary">actif</span>
                      </div>
                      <div class="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                        <span class="flex items-center">
                          <CubeIcon class="h-3 w-3 mr-1" />
                          {{ env.backend }}
                        </span>
                        <span class="flex items-center">
                          <ArchiveBoxIcon class="h-3 w-3 mr-1" />
                          {{ env.package_count }} packages
                        </span>
                        <span class="flex items-center">
                          <ClockIcon class="h-3 w-3 mr-1" />
                          {{ formatRelativeTime(env.last_used || env.created_at) }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center space-x-3">
                    <span class="text-sm font-medium text-gray-700">{{ formatSize(env.size_mb) }}</span>
                    <ArrowRightIcon class="h-5 w-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions rapides avec design moderne -->
          <div class="bg-white rounded-xl shadow-lg border border-gray-200">
            <div class="p-6 border-b border-gray-200">
              <h3 class="text-xl font-semibold text-gray-900">Actions rapides</h3>
              <p class="text-sm text-gray-500 mt-1">Raccourcis vers les fonctionnalités principales</p>
            </div>
            <div class="p-6">
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <router-link
                  to="/templates"
                  class="group p-4 border-2 border-gray-100 rounded-lg hover:border-green-200 hover:bg-green-50/50 transition-all duration-200"
                >
                  <div class="flex items-center space-x-3">
                    <div class="p-2 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                      <DocumentTextIcon class="h-6 w-6 text-green-600" />
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-900">Templates</h4>
                      <p class="text-sm text-gray-500">Projets pré-configurés</p>
                    </div>
                  </div>
                </router-link>
                
                <router-link
                  to="/cache"
                  class="group p-4 border-2 border-gray-100 rounded-lg hover:border-orange-200 hover:bg-orange-50/50 transition-all duration-200"
                >
                  <div class="flex items-center space-x-3">
                    <div class="p-2 bg-orange-100 rounded-lg group-hover:bg-orange-200 transition-colors">
                      <CircleStackIcon class="h-6 w-6 text-orange-600" />
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-900">Cache</h4>
                      <p class="text-sm text-gray-500">Gestion offline</p>
                    </div>
                  </div>
                </router-link>
                
                <button
                  @click="runQuickDoctor"
                  :disabled="runningDoctor"
                  class="group p-4 border-2 border-gray-100 rounded-lg hover:border-blue-200 hover:bg-blue-50/50 transition-all duration-200 disabled:opacity-50"
                >
                  <div class="flex items-center space-x-3">
                    <div class="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                      <div v-if="runningDoctor" class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                      <HeartIcon v-else class="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-900">Diagnostic</h4>
                      <p class="text-sm text-gray-500">Vérification système</p>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar droite avec informations système -->
        <div class="space-y-6">
          <!-- Santé du système avec design moderne -->
          <div class="bg-white rounded-xl shadow-lg border border-gray-200">
            <div class="p-6 border-b border-gray-200">
              <div class="flex items-center justify-between">
                <h3 class="text-lg font-semibold text-gray-900">Santé du système</h3>
                <div class="flex items-center space-x-2">
                  <div
                    class="w-3 h-3 rounded-full"
                    :class="systemHealth === 'healthy' ? 'bg-green-400' : systemHealth === 'warning' ? 'bg-yellow-400' : 'bg-red-400'"
                  ></div>
                  <span class="text-sm font-medium" :class="getHealthTextColor(systemHealth)">
                    {{ getHealthText(systemHealth) }}
                  </span>
                </div>
              </div>
            </div>
            
            <div class="p-6">
              <div v-if="systemInfo" class="space-y-4">
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div class="flex items-center space-x-2">
                    <CommandLineIcon class="h-4 w-4 text-gray-600" />
                    <span class="text-sm font-medium text-gray-700">Python</span>
                  </div>
                  <span class="text-sm font-mono text-gray-900">{{ systemInfo.python_version }}</span>
                </div>
                
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div class="flex items-center space-x-2">
                    <CogIcon class="h-4 w-4 text-gray-600" />
                    <span class="text-sm font-medium text-gray-700">GestVenv</span>
                  </div>
                  <span class="text-sm font-mono text-gray-900">{{ systemInfo.gestvenv_version }}</span>
                </div>
                
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div class="flex items-center space-x-2">
                    <CubeIcon class="h-4 w-4 text-gray-600" />
                    <span class="text-sm font-medium text-gray-700">Backends</span>
                  </div>
                  <div class="flex space-x-1">
                    <span
                      v-for="backend in systemInfo.backends_available"
                      :key="backend"
                      class="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800"
                    >
                      {{ backend }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Opérations récentes avec design moderne -->
          <div class="bg-white rounded-xl shadow-lg border border-gray-200">
            <div class="p-6 border-b border-gray-200">
              <div class="flex items-center justify-between">
                <h3 class="text-lg font-semibold text-gray-900">Activité récente</h3>
                <router-link
                  to="/operations"
                  class="text-blue-600 hover:text-blue-700 font-medium text-sm flex items-center space-x-1 transition-colors"
                >
                  <span>Voir tout</span>
                  <ArrowRightIcon class="h-4 w-4" />
                </router-link>
              </div>
            </div>
            
            <div class="p-6">
              <div v-if="recentOperations.length === 0" class="text-center py-8">
                <div class="bg-gray-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                  <ClipboardDocumentListIcon class="h-8 w-8 text-gray-400" />
                </div>
                <p class="text-sm text-gray-500">Aucune opération récente</p>
              </div>
              
              <div v-else class="space-y-3">
                <div
                  v-for="operation in recentOperations.slice(0, 4)"
                  :key="operation.id"
                  class="flex items-center space-x-3 p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center"
                    :class="getOperationIconBg(operation.status)"
                  >
                    <component :is="getOperationIcon(operation.type)" class="h-4 w-4 text-white" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">{{ getOperationTitle(operation.type) }}</p>
                    <p class="text-xs text-gray-500 truncate">{{ formatRelativeTime(operation.started_at) }}</p>
                  </div>
                  <span class="badge badge-sm" :class="getOperationStatusClass(operation.status)">
                    {{ getOperationStatusText(operation.status) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Raccourcis système -->
          <div class="bg-white rounded-xl shadow-lg border border-gray-200">
            <div class="p-6 border-b border-gray-200">
              <h3 class="text-lg font-semibold text-gray-900">Maintenance</h3>
            </div>
            <div class="p-6 space-y-3">
              <button
                @click="cleanupSystem"
                :disabled="runningCleanup"
                class="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <div v-if="runningCleanup" class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                <TrashIcon v-else class="h-4 w-4 mr-2" />
                Nettoyer le système
              </button>
              
              <router-link
                to="/system"
                class="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                <CogIcon class="h-4 w-4 mr-2" />
                Paramètres système
              </router-link>
            </div>
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
  ArrowUpIcon,
  HeartIcon,
  DocumentTextIcon,
  TrashIcon,
  SparklesIcon,
  ClockIcon,
  CogIcon,
  CommandLineIcon,
  CubeIcon,
  ArchiveBoxIcon,
  FolderPlusIcon,
  CloudIcon,
  WrenchIcon
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
const systemHealth = computed(() => systemStore.systemHealth || 'healthy')
const runningOperations = computed(() => systemStore.runningOperations || [])
const recentOperations = computed(() => systemStore.recentOperations || [])

const healthyEnvironments = computed(() => {
  return environmentsStore.filteredEnvironments.filter(env => env.status === 'healthy').length
})

const cacheHitRate = computed(() => {
  return systemStore.cacheInfo?.hit_rate ? Math.round(systemStore.cacheInfo.hit_rate * 100) : 85
})

const completedToday = computed(() => {
  const today = new Date().toDateString()
  return recentOperations.value.filter(op => 
    op.completed_at && new Date(op.completed_at).toDateString() === today
  ).length
})

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
function formatLastActivity() {
  if (recentOperations.value.length === 0) return 'Aucune activité'
  const latest = recentOperations.value[0]
  return formatRelativeTime(latest.started_at)
}

function formatCacheSize() {
  const cacheInfo = systemStore.cacheInfo
  if (!cacheInfo?.total_size_mb) return '0 MB'
  return formatSize(cacheInfo.total_size_mb)
}

function getEnvironmentBgColor(backend: string) {
  switch (backend.toLowerCase()) {
    case 'pip': return 'bg-gradient-to-br from-blue-500 to-blue-600'
    case 'uv': return 'bg-gradient-to-br from-purple-500 to-purple-600'
    case 'poetry': return 'bg-gradient-to-br from-indigo-500 to-indigo-600'
    case 'pdm': return 'bg-gradient-to-br from-green-500 to-green-600'
    default: return 'bg-gradient-to-br from-gray-500 to-gray-600'
  }
}

function getBackendIcon(backend: string) {
  switch (backend.toLowerCase()) {
    case 'pip': return CubeIcon
    case 'uv': return SparklesIcon
    case 'poetry': return DocumentTextIcon
    case 'pdm': return ArchiveBoxIcon
    default: return CubeIcon
  }
}

function getStatusColor(status: string) {
  switch (status) {
    case 'healthy': return 'bg-green-400'
    case 'warning': return 'bg-yellow-400'
    case 'error': return 'bg-red-400'
    case 'creating': return 'bg-blue-400'
    default: return 'bg-gray-400'
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

function getHealthTextColor(health: string) {
  switch (health) {
    case 'healthy': return 'text-green-600'
    case 'warning': return 'text-yellow-600'
    case 'error': return 'text-red-600'
    default: return 'text-gray-600'
  }
}

function getOperationIcon(type: string) {
  switch (type) {
    case 'environment_create': return FolderPlusIcon
    case 'package_install': return ArchiveBoxIcon
    case 'cache_clean': return TrashIcon
    case 'system_doctor': return WrenchIcon
    default: return CogIcon
  }
}

function getOperationIconBg(status: string) {
  switch (status) {
    case 'completed': return 'bg-green-500'
    case 'running': return 'bg-blue-500'
    case 'failed': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

function getOperationTitle(type: string) {
  switch (type) {
    case 'environment_create': return 'Création environnement'
    case 'environment_delete': return 'Suppression environnement'
    case 'package_install': return 'Installation package'
    case 'package_uninstall': return 'Désinstallation package'
    case 'cache_clean': return 'Nettoyage cache'
    case 'system_doctor': return 'Diagnostic système'
    default: return type
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

function getOperationStatusText(status: string) {
  switch (status) {
    case 'completed': return 'Terminé'
    case 'running': return 'En cours'
    case 'failed': return 'Échoué'
    case 'cancelled': return 'Annulé'
    default: return status
  }
}

function formatSize(sizeMb: number) {
  if (sizeMb < 1024) {
    return `${sizeMb.toFixed(1)} MB`
  }
  return `${(sizeMb / 1024).toFixed(1)} GB`
}

function formatRelativeTime(date: string) {
  const now = new Date()
  const past = new Date(date)
  const diffMs = now.getTime() - past.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'À l\'instant'
  if (diffMins < 60) return `Il y a ${diffMins} min`
  if (diffMins < 1440) return `Il y a ${Math.floor(diffMins / 60)} h`
  return `Il y a ${Math.floor(diffMins / 1440)} j`
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
    await systemStore.cleanupSystem(true, false)
  } catch (error) {
    console.error('Failed to cleanup system:', error)
  } finally {
    runningCleanup.value = false
  }
}

// Lifecycle
onMounted(async () => {
  if (environmentsStore.totalEnvironments === 0) {
    environmentsStore.initialize()
  }
  
  // Charger les informations système si pas encore fait
  if (!systemStore.systemInfo) {
    systemStore.fetchSystemInfo()
  }
})
</script>