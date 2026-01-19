<template>
  <div class="container mx-auto p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold">Système</h1>
      <p class="text-gray-500 mt-2">Informations système et outils de diagnostic</p>
    </div>

    <!-- System Info Cards -->
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-6">
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <Monitor :size="16" class="mr-2" />
            Système d'exploitation
          </h3>
        </div>
        <div class="card-body">
          <div class="text-xl font-bold">{{ systemInfo?.os || 'Chargement...' }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <Code2 :size="16" class="mr-2" />
            Version Python
          </h3>
        </div>
        <div class="card-body">
          <div class="text-xl font-bold">{{ systemInfo?.python_version || 'Chargement...' }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <Package :size="16" class="mr-2" />
            Version GestVenv
          </h3>
        </div>
        <div class="card-body">
          <div class="text-xl font-bold">{{ systemInfo?.gestvenv_version || 'Chargement...' }}</div>
        </div>
      </div>
    </div>

    <!-- Disk Usage -->
    <div class="card mb-6">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Utilisation du disque</h2>
      </div>
      <div class="card-body">
        <div class="space-y-4">
          <div v-for="(usage, path) in systemInfo?.disk_usage" :key="path">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium">{{ path }}</span>
              <span class="text-sm text-gray-500">
                {{ formatSize(usage.used) }} / {{ formatSize(usage.total) }}
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div 
                class="h-2 rounded-full bg-primary-600 transition-all duration-300"
                :style="{ width: `${(usage.used / usage.total) * 100}%` }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Memory Usage -->
    <div class="card mb-6">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Utilisation de la mémoire</h2>
      </div>
      <div class="card-body">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-500">Mémoire utilisée</p>
            <p class="text-2xl font-bold">{{ formatSize(systemInfo?.memory_usage?.used || 0) }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-500">Mémoire totale</p>
            <p class="text-2xl font-bold">{{ formatSize(systemInfo?.memory_usage?.total || 0) }}</p>
          </div>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2 mt-4">
          <div 
            class="h-2 rounded-full bg-primary-600 transition-all duration-300"
            :style="{ width: `${((systemInfo?.memory_usage?.used || 0) / (systemInfo?.memory_usage?.total || 1)) * 100}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Available Backends -->
    <div class="card mb-6">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Backends disponibles</h2>
      </div>
      <div class="card-body">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="backend in availableBackends"
            :key="backend"
            class="flex items-center space-x-2"
          >
            <CheckCircle2 
              v-if="systemInfo?.backends_available?.includes(backend)"
              :size="16" 
              class="text-green-500" 
            />
            <XCircle 
              v-else
              :size="16" 
              class="text-red-500" 
            />
            <span>{{ backend.toUpperCase() }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- System Health -->
    <div class="card mb-6">
      <div class="card-header">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-semibold">Santé du système</h2>
          <button
            class="btn btn-outline btn-sm"
            @click="runHealthCheck"
            :disabled="isCheckingHealth"
          >
            <RefreshCw :size="16" class="mr-2" :class="{ 'animate-spin': isCheckingHealth }" />
            Vérifier
          </button>
        </div>
      </div>
      <div class="card-body">
        <div v-if="systemHealth" class="space-y-4">
          <!-- Health Status -->
          <div class="flex items-center space-x-2">
            <div
              class="h-3 w-3 rounded-full"
              :class="{
                'bg-green-500': systemHealth.status === 'healthy',
                'bg-yellow-500': systemHealth.status === 'warning',
                'bg-red-500': systemHealth.status === 'error'
              }"
            />
            <span class="font-medium">
              {{ healthStatusText }}
            </span>
          </div>

          <!-- Health Checks -->
          <div class="space-y-2">
            <div
              v-for="(check, index) in systemHealth.checks"
              :key="index"
              class="flex items-center justify-between p-2 rounded-lg bg-gray-100"
            >
              <div class="flex items-center space-x-2">
                <CheckCircle2 
                  v-if="check.status === 'pass'"
                  :size="16" 
                  class="text-green-500" 
                />
                <AlertTriangle
                  v-else-if="check.status === 'warning'"
                  :size="16" 
                  class="text-yellow-500" 
                />
                <XCircle 
                  v-else
                  :size="16" 
                  class="text-red-500" 
                />
                <span class="text-sm">{{ check.name }}</span>
              </div>
              <span class="text-sm text-gray-500">{{ check.message }}</span>
            </div>
          </div>

          <!-- Recommendations -->
          <div v-if="systemHealth.recommendations?.length > 0">
            <h4 class="font-medium mb-2">Recommandations</h4>
            <ul class="space-y-1">
              <li
                v-for="(rec, index) in systemHealth.recommendations"
                :key="index"
                class="text-sm text-gray-500 flex items-start"
              >
                <span class="mr-2">•</span>
                <span>{{ rec }}</span>
              </li>
            </ul>
          </div>
        </div>
        <div v-else class="text-center py-8">
          <HeartHandshake :size="48" class="mx-auto text-gray-500 mb-4" />
          <p class="text-gray-500">
            Cliquez sur "Vérifier" pour analyser la santé du système
          </p>
        </div>
      </div>
    </div>

    <!-- System Actions -->
    <div class="card">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Actions système</h2>
      </div>
      <div class="card-body">
        <div class="flex flex-wrap gap-4">
          <button
            class="btn btn-outline"
            @click="runDoctor"
            :disabled="isRunningDoctor"
          >
            <Wrench :size="16" class="mr-2" />
            Diagnostic et réparation
          </button>
          
          <button
            class="btn btn-outline"
            @click="showCleanupDialog = true"
            :disabled="isCleaningUp"
          >
            <Sparkles :size="16" class="mr-2" />
            Nettoyage système
          </button>
          
          <button
            class="btn btn-outline"
            @click="refreshSystemInfo"
            :disabled="isLoading"
          >
            <RefreshCw :size="16" class="mr-2" :class="{ 'animate-spin': isLoading }" />
            Actualiser
          </button>
        </div>
      </div>
    </div>

    <!-- Cleanup Dialog -->
    <div v-if="showCleanupDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Nettoyage système</h3>
          <p class="text-sm text-gray-500 mt-1">
            Supprimez les fichiers temporaires et optimisez le système.
          </p>
        </div>
        
        <div class="space-y-4">
          <div class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div class="flex items-start">
              <AlertCircle :size="16" class="mr-2 text-yellow-600 mt-0.5" />
              <div>
                <h4 class="text-sm font-medium text-yellow-900">Attention</h4>
                <p class="text-sm text-yellow-700 mt-1">
                  Cette action supprimera les fichiers temporaires et les logs anciens. 
                  Les environnements et packages ne seront pas affectés.
                </p>
              </div>
            </div>
          </div>
          
          <div class="space-y-2">
            <div class="flex items-center space-x-2">
              <input type="checkbox" id="clean-temp" v-model="cleanupOptions.temp_files" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              <label for="clean-temp" class="text-sm font-medium text-gray-700">Fichiers temporaires</label>
            </div>
            <div class="flex items-center space-x-2">
              <input type="checkbox" id="clean-logs" v-model="cleanupOptions.old_logs" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              <label for="clean-logs" class="text-sm font-medium text-gray-700">Anciens logs (> 30 jours)</label>
            </div>
            <div class="flex items-center space-x-2">
              <input type="checkbox" id="clean-cache" v-model="cleanupOptions.unused_cache" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              <label for="clean-cache" class="text-sm font-medium text-gray-700">Cache non utilisé</label>
            </div>
          </div>
        </div>
        
        <div class="flex justify-end space-x-2 mt-6">
          <button class="btn btn-outline" @click="showCleanupDialog = false">
            Annuler
          </button>
          <button
            class="btn btn-primary"
            @click="runCleanup"
            :disabled="isCleaningUp || !hasCleanupSelection"
          >
            <Loader2 v-if="isCleaningUp" :size="16" class="mr-2 animate-spin" />
            Nettoyer
          </button>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div v-if="successMessage" class="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
      <div class="flex items-start">
        <CheckCircle2 :size="16" class="mr-2 text-green-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-green-900">Succès</h4>
          <p class="text-sm text-green-700 mt-1">{{ successMessage }}</p>
        </div>
      </div>
    </div>

    <div v-if="error" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
      <div class="flex items-start">
        <AlertCircle :size="16" class="mr-2 text-red-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-red-900">Erreur</h4>
          <p class="text-sm text-red-700 mt-1">{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/services/api'
import {
  Monitor,
  Code2,
  Package,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HeartHandshake,
  Wrench,
  Sparkles,
  AlertCircle,
  Loader2
} from 'lucide-vue-next'

// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  // For now, using console.log - can be replaced with a proper notification system
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}

// State
const systemInfo = ref<any>(null)
const systemHealth = ref<any>(null)
const isLoading = ref(false)
const isCheckingHealth = ref(false)
const isRunningDoctor = ref(false)
const isCleaningUp = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Dialog states
const showCleanupDialog = ref(false)
const cleanupOptions = ref({
  temp_files: true,
  old_logs: true,
  unused_cache: false
})

// Constants
const availableBackends = ['pip', 'uv', 'poetry', 'pdm']

// Computed
const healthStatusText = computed(() => {
  switch (systemHealth.value?.status) {
    case 'healthy': return 'Système en bonne santé'
    case 'warning': return 'Avertissements détectés'
    case 'error': return 'Problèmes détectés'
    default: return 'État inconnu'
  }
})

const hasCleanupSelection = computed(() => {
  return Object.values(cleanupOptions.value).some(v => v)
})

// Methods
const formatSize = (bytes: number) => {
  const mb = bytes / (1024 * 1024)
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

const loadSystemInfo = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    systemInfo.value = await api.getSystemInfo()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du chargement'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isLoading.value = false
  }
}

const runHealthCheck = async () => {
  isCheckingHealth.value = true
  error.value = null
  
  try {
    systemHealth.value = await api.getSystemHealth()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la vérification'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isCheckingHealth.value = false
  }
}

const runDoctor = async () => {
  isRunningDoctor.value = true
  error.value = null
  
  try {
    const result = await api.runDoctor()
    
    // Refresh system info and health
    await Promise.all([
      loadSystemInfo(),
      runHealthCheck()
    ])
    
    showToast({
      title: 'Succès',
      description: result.message || 'Diagnostic et réparation terminés'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du diagnostic'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isRunningDoctor.value = false
  }
}

const runCleanup = async () => {
  isCleaningUp.value = true
  error.value = null
  
  try {
    const result = await api.cleanupSystem({
      orphaned_only: cleanupOptions.value.temp_files,
      clean_cache: cleanupOptions.value.unused_cache
    })
    
    showCleanupDialog.value = false
    
    // Refresh system info
    await loadSystemInfo()
    
    showToast({
      title: 'Succès',
      description: result.message || 'Nettoyage terminé'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du nettoyage'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isCleaningUp.value = false
  }
}

const refreshSystemInfo = async () => {
  await Promise.all([
    loadSystemInfo(),
    runHealthCheck()
  ])
  successMessage.value = 'Informations système actualisées'
  setTimeout(() => { successMessage.value = null }, 3000)
}

// Lifecycle
onMounted(() => {
  loadSystemInfo()
})

// Clear messages after timeout
watch([error, successMessage], () => {
  if (error.value || successMessage.value) {
    setTimeout(() => {
      error.value = null
      successMessage.value = null
    }, 5000)
  }
})
</script>