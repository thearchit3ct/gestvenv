<template>
  <div class="container mx-auto p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold">Cache</h1>
      <p class="text-gray-500 mt-2">Gérez le cache des packages pour une utilisation hors ligne</p>
    </div>

    <!-- Cache Overview -->
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <HardDrive :size="16" class="mr-2" />
            Taille totale
          </h3>
        </div>
        <div class="card-body">
          <div class="text-2xl font-bold">{{ formatSize(cacheInfo?.total_size_mb || 0) }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <Package :size="16" class="mr-2" />
            Packages en cache
          </h3>
        </div>
        <div class="card-body">
          <div class="text-2xl font-bold">{{ cacheInfo?.package_count || 0 }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <TrendingUp :size="16" class="mr-2" />
            Taux de succès
          </h3>
        </div>
        <div class="card-body">
          <div class="text-2xl font-bold">{{ formatPercent(cacheInfo?.hit_rate || 0) }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <Clock :size="16" class="mr-2" />
            Dernier nettoyage
          </h3>
        </div>
        <div class="card-body">
          <div class="text-lg font-medium">
            {{ cacheInfo?.last_cleanup ? formatRelativeTime(cacheInfo.last_cleanup) : 'Jamais' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Cache Actions -->
    <div class="card mb-6">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Actions du cache</h2>
      </div>
      <div class="card-body">
        <div class="flex flex-wrap gap-4">
          <button 
            class="btn btn-outline" 
            @click="refreshCacheInfo"
            :disabled="isLoading"
          >
            <RefreshCw :size="16" class="mr-2" :class="{ 'animate-spin': isLoading }" />
            Actualiser
          </button>
          
          <button 
            class="btn btn-outline"
            @click="showCleanDialog = true"
            :disabled="isCleaning"
          >
            <Trash2 :size="16" class="mr-2" />
            Nettoyer le cache
          </button>
          
          <button 
            class="btn btn-outline"
            @click="showExportDialog = true"
            :disabled="isExporting"
          >
            <Download :size="16" class="mr-2" />
            Exporter
          </button>
          
          <button 
            class="btn btn-outline"
            @click="showImportDialog = true"
            :disabled="isImporting"
          >
            <Upload :size="16" class="mr-2" />
            Importer
          </button>
        </div>
      </div>
    </div>

    <!-- Cache Location -->
    <div class="card mb-6">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Emplacement du cache</h2>
      </div>
      <div class="card-body">
        <div class="flex items-center space-x-4">
          <FolderOpen :size="20" class="text-gray-500" />
          <code class="flex-1 p-2 bg-muted rounded-md font-mono text-sm">
            {{ cacheInfo?.location || 'Chargement...' }}
          </code>
          <button
            class="btn btn-ghost btn-sm"
            @click="copyLocation"
          >
            <Copy :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- Clean Cache Dialog -->
    <div v-if="showCleanDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Nettoyer le cache</h3>
          <p class="text-sm text-gray-500 mt-1">
            Cette action supprimera les packages en cache non utilisés. Les packages actuellement installés seront conservés.
          </p>
        </div>
        
        <div class="space-y-4">
          <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div class="flex items-start">
              <AlertCircle :size="16" class="mr-2 text-blue-600 mt-0.5" />
              <div>
                <h4 class="text-sm font-medium text-blue-900">Information</h4>
                <p class="text-sm text-blue-700 mt-1">
                  Le nettoyage libérera environ {{ estimatedCleanSize }} d'espace disque.
                </p>
              </div>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <input type="checkbox" id="force-clean" v-model="forceClean" class="mr-2" />
            <label for="force-clean" class="form-label">Forcer le nettoyage complet (supprime tout le cache)</label>
          </div>
        </div>
        
        <div class="flex justify-end space-x-2 mt-4">
          <button class="btn btn-outline" @click="showCleanDialog = false">
            Annuler
          </button>
          <button
            class="btn btn-danger"
            @click="cleanCache"
            :disabled="isCleaning"
          >
            <Loader2 v-if="isCleaning" :size="16" class="mr-2 animate-spin" />
            Nettoyer
          </button>
        </div>
      </div>
    </div>

    <!-- Export Dialog -->
    <div v-if="showExportDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Exporter le cache</h3>
          <p class="text-sm text-gray-500 mt-1">
            Exportez le cache vers un fichier pour le partager ou le sauvegarder.
          </p>
        </div>
        
        <div class="space-y-4">
          <div>
            <label for="export-path" class="form-label">Chemin de destination</label>
            <input
              id="export-path"
              v-model="exportPath"
              placeholder="/path/to/export/cache.tar.gz"
              class="form-input"
            />
          </div>

          <div class="flex items-center space-x-2">
            <input type="checkbox" id="compress" v-model="exportCompress" class="mr-2" />
            <label for="compress" class="form-label">Compresser l'archive</label>
          </div>

          <div class="flex items-center space-x-2">
            <input type="checkbox" id="include-metadata" v-model="exportIncludeMetadata" class="mr-2" />
            <label for="include-metadata" class="form-label">Inclure les métadonnées</label>
          </div>
        </div>
        
        <div class="flex justify-end space-x-2 mt-4">
          <button class="btn btn-outline" @click="showExportDialog = false">
            Annuler
          </button>
          <button
            class="btn btn-primary"
            @click="exportCache"
            :disabled="!exportPath.trim() || isExporting"
          >
            <Loader2 v-if="isExporting" :size="16" class="mr-2 animate-spin" />
            Exporter
          </button>
        </div>
      </div>
    </div>

    <!-- Import Dialog -->
    <div v-if="showImportDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Importer un cache</h3>
          <p class="text-sm text-gray-500 mt-1">
            Importez un cache depuis un fichier d'archive.
          </p>
        </div>
        
        <div class="space-y-4">
          <div>
            <label for="import-path" class="form-label">Chemin du fichier</label>
            <input
              id="import-path"
              v-model="importPath"
              placeholder="/path/to/cache.tar.gz"
              class="form-input"
            />
          </div>
          
          <div class="flex items-center space-x-2">
            <input type="checkbox" id="merge" v-model="importMerge" class="mr-2" />
            <label for="merge" class="form-label">Fusionner avec le cache existant</label>
          </div>
          
          <div class="flex items-center space-x-2">
            <input type="checkbox" id="verify" v-model="importVerify" class="mr-2" />
            <label for="verify" class="form-label">Vérifier l'intégrité des packages</label>
          </div>
        </div>
        
        <div class="flex justify-end space-x-2 mt-4">
          <button class="btn btn-outline" @click="showImportDialog = false">
            Annuler
          </button>
          <button
            class="btn btn-primary"
            @click="importCache"
            :disabled="!importPath.trim() || isImporting"
          >
            <Loader2 v-if="isImporting" :size="16" class="mr-2 animate-spin" />
            Importer
          </button>
        </div>
      </div>
    </div>

    <!-- Success/Error Messages -->
    <div v-if="successMessage" class="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
      <div class="flex items-start">
        <CheckCircle2 :size="16" class="mr-2 text-green-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-green-900">Succès</h4>
          <p class="text-sm text-green-700 mt-1">{{ successMessage }}</p>
        </div>
      </div>
    </div>

    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
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
import { ref, onMounted, watch } from 'vue'
// Toast functionality will be implemented locally
import { api } from '@/services/api'
import {
  HardDrive,
  Package,
  TrendingUp,
  Clock,
  RefreshCw,
  Trash2,
  Download,
  Upload,
  FolderOpen,
  Copy,
  AlertCircle,
  CheckCircle2,
  Loader2
} from 'lucide-vue-next'
// Using custom CSS classes from style.css

// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  // For now, using console.log - can be replaced with a proper notification system
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}

// State
const cacheInfo = ref<any>(null)
const isLoading = ref(false)
const isCleaning = ref(false)
const isExporting = ref(false)
const isImporting = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Dialog states
const showCleanDialog = ref(false)
const showExportDialog = ref(false)
const showImportDialog = ref(false)

// Form states
const forceClean = ref(false)
const exportPath = ref('')
const exportCompress = ref(true)
const exportIncludeMetadata = ref(true)
const importPath = ref('')
const importMerge = ref(false)
const importVerify = ref(true)

// Computed
const estimatedCleanSize = ref('0 MB')

// Methods
const formatSize = (mb: number) => {
  if (mb < 1) return `${(mb * 1024).toFixed(1)} KB`
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

const formatPercent = (rate: number) => {
  return `${(rate * 100).toFixed(1)}%`
}

const formatRelativeTime = (date: string) => {
  const now = new Date()
  const past = new Date(date)
  const diffMs = now.getTime() - past.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return "Aujourd'hui"
  if (diffDays === 1) return "Hier"
  if (diffDays < 7) return `Il y a ${diffDays} jours`
  if (diffDays < 30) return `Il y a ${Math.floor(diffDays / 7)} semaines`
  return `Il y a ${Math.floor(diffDays / 30)} mois`
}

const loadCacheInfo = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await api.getCacheInfo()
    cacheInfo.value = response
    
    // Estimate clean size (rough calculation)
    if (response.total_size_mb > 0) {
      const unusedPercent = 1 - response.hit_rate
      const cleanableMb = response.total_size_mb * unusedPercent * 0.7 // 70% of unused
      estimatedCleanSize.value = formatSize(cleanableMb)
    }
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

const refreshCacheInfo = async () => {
  await loadCacheInfo()
  successMessage.value = 'Informations du cache actualisées'
  setTimeout(() => { successMessage.value = null }, 3000)
}

const copyLocation = async () => {
  if (cacheInfo.value?.location) {
    await navigator.clipboard.writeText(cacheInfo.value.location)
    showToast({
      title: 'Copié',
      description: 'Chemin copié dans le presse-papiers'
    })
  }
}

const cleanCache = async () => {
  isCleaning.value = true
  error.value = null
  
  try {
    await api.cleanCache(forceClean.value ? {} : { older_than: 30 })
    showCleanDialog.value = false
    forceClean.value = false
    
    await loadCacheInfo()
    
    showToast({
      title: 'Succès',
      description: 'Cache nettoyé avec succès'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du nettoyage'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isCleaning.value = false
  }
}

const exportCache = async () => {
  if (!exportPath.value.trim()) return
  
  isExporting.value = true
  error.value = null
  
  try {
    await api.exportCache(exportPath.value, exportCompress.value)
    
    showExportDialog.value = false
    exportPath.value = ''
    
    showToast({
      title: 'Succès',
      description: 'Cache exporté avec succès'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de l\'export'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isExporting.value = false
  }
}

const importCache = async () => {
  if (!importPath.value.trim()) return
  
  isImporting.value = true
  error.value = null
  
  try {
    await api.importCache(importPath.value, importMerge.value, importVerify.value)
    
    showImportDialog.value = false
    importPath.value = ''
    
    await loadCacheInfo()
    
    showToast({
      title: 'Succès',
      description: 'Cache importé avec succès'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de l\'import'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isImporting.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadCacheInfo()
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