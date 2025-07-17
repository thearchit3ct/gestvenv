<template>
  <div class="container mx-auto p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold">Opérations</h1>
      <p class="text-muted-foreground mt-2">Historique et suivi des opérations en cours</p>
    </div>

    <!-- Operations Summary -->
    <div class="grid gap-4 md:grid-cols-3 mb-6">
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <PlayCircle :size="16" class="mr-2" />
            En cours
          </h3>
        </div>
        <div class="card-body">
          <div class="text-2xl font-bold">{{ runningCount }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <CheckCircle2 :size="16" class="mr-2" />
            Terminées
          </h3>
        </div>
        <div class="card-body">
          <div class="text-2xl font-bold">{{ completedCount }}</div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header pb-3">
          <h3 class="text-sm font-medium text-gray-500 flex items-center">
            <XCircle :size="16" class="mr-2" />
            Échouées
          </h3>
        </div>
        <div class="card-body">
          <div class="text-2xl font-bold">{{ failedCount }}</div>
        </div>
      </div>
    </div>

    <!-- Active Operations -->
    <div v-if="activeOperations.length > 0" class="card mb-6">
      <div class="card-header">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-semibold">Opérations actives</h2>
          <button
            class="btn btn-outline btn-sm"
            @click="refreshOperations"
            :disabled="isLoading"
          >
            <RefreshCw :size="16" class="mr-2" :class="{ 'animate-spin': isLoading }" />
            Actualiser
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="space-y-4">
          <div
            v-for="operation in activeOperations"
            :key="operation.id"
            class="border rounded-lg p-4"
          >
            <div class="flex items-start justify-between mb-2">
              <div>
                <h4 class="font-medium">{{ getOperationTitle(operation.type) }}</h4>
                <p class="text-sm text-gray-500">
                  Démarré {{ formatRelativeTime(operation.started_at) }}
                </p>
              </div>
              <span class="badge" :class="getStatusBadgeClass(operation.status)">
                {{ getStatusText(operation.status) }}
              </span>
            </div>
            
            <div class="space-y-2">
              <p class="text-sm">{{ operation.message }}</p>
              <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 transition-all duration-300" :style="{ width: operation.progress + '%' }"></div>
              </div>
              <div class="flex items-center justify-between text-xs text-gray-500">
                <span>{{ operation.progress }}%</span>
                <button
                  v-if="operation.status === 'running'"
                  class="btn btn-ghost btn-sm"
                  @click="cancelOperation(operation.id)"
                >
                  <Ban :size="14" class="mr-1" />
                  Annuler
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Operations Filter -->
    <div class="card mb-4">
      <div class="card-body p-4">
        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[200px]">
            <div class="relative">
              <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="searchQuery"
                placeholder="Rechercher dans l'historique..."
                class="pl-9"
              />
            </div>
          </div>
          
          <Select v-model="statusFilter">
            <SelectTrigger class="w-[150px]">
              <SelectValue placeholder="Statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous</SelectItem>
              <SelectItem value="pending">En attente</SelectItem>
              <SelectItem value="running">En cours</SelectItem>
              <SelectItem value="completed">Terminé</SelectItem>
              <SelectItem value="failed">Échoué</SelectItem>
              <SelectItem value="cancelled">Annulé</SelectItem>
            </SelectContent>
          </Select>
          
          <Select v-model="typeFilter">
            <SelectTrigger class="w-[200px]">
              <SelectValue placeholder="Type d'opération" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les types</SelectItem>
              <SelectItem value="environment_create">Création d'environnement</SelectItem>
              <SelectItem value="environment_delete">Suppression d'environnement</SelectItem>
              <SelectItem value="package_install">Installation de package</SelectItem>
              <SelectItem value="package_uninstall">Désinstallation de package</SelectItem>
              <SelectItem value="package_update">Mise à jour de package</SelectItem>
              <SelectItem value="cache_clean">Nettoyage du cache</SelectItem>
              <SelectItem value="cache_export">Export du cache</SelectItem>
              <SelectItem value="cache_import">Import du cache</SelectItem>
              <SelectItem value="system_doctor">Diagnostic système</SelectItem>
              <SelectItem value="system_cleanup">Nettoyage système</SelectItem>
            </SelectContent>
          </select>
        </div>
      </div>
    </div>

    <!-- Operations History -->
    <div class="card">
      <div class="card-header">
        <h2 class="text-xl font-semibold">Historique des opérations</h2>
      </div>
      <div class="card-body">
        <div v-if="filteredOperations.length > 0" class="space-y-2">
          <div
            v-for="operation in paginatedOperations"
            :key="operation.id"
            class="flex items-center justify-between p-3 rounded-lg hover:bg-gray-100/50 transition-colors cursor-pointer"
            @click="viewOperationDetails(operation)"
          >
            <div class="flex items-center space-x-3">
              <component
                :is="getOperationIcon(operation.type)"
                :size="20"
                class="text-muted-foreground"
              />
              <div>
                <p class="font-medium text-sm">{{ getOperationTitle(operation.type) }}</p>
                <p class="text-xs text-muted-foreground">
                  {{ formatDate(operation.started_at) }}
                  <span v-if="operation.completed_at">
                    • Durée: {{ formatDuration(operation.started_at, operation.completed_at) }}
                  </span>
                </p>
              </div>
            </div>
            
            <div class="flex items-center space-x-2">
              <span class="badge" :class="getStatusBadgeClass(operation.status)">
                {{ getStatusText(operation.status) }}
              </span>
              <ChevronRight :size="16" class="text-gray-500" />
            </div>
          </div>
        </div>
        
        <div v-else class="text-center py-12">
          <History :size="48" class="mx-auto text-gray-400 mb-4" />
          <p class="text-gray-500">
            {{ searchQuery || statusFilter !== 'all' || typeFilter !== 'all' 
              ? 'Aucune opération trouvée' 
              : 'Aucune opération dans l\'historique' }}
          </p>
        </div>
        
        <!-- Pagination -->
        <div v-if="totalPages > 1" class="mt-4 flex items-center justify-center space-x-2">
          <button
            class="btn btn-outline btn-sm"
            @click="currentPage--"
            :disabled="currentPage === 1"
          >
            <ChevronLeft :size="16" />
          </button>
          
          <span class="text-sm text-gray-500">
            Page {{ currentPage }} sur {{ totalPages }}
          </span>
          
          <button
            class="btn btn-outline btn-sm"
            @click="currentPage++"
            :disabled="currentPage === totalPages"
          >
            <ChevronRight :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- Operation Details Dialog -->
    <div v-if="showDetailsDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Détails de l'opération</h3>
        </div>
        
        <div v-if="selectedOperation" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-sm font-medium text-muted-foreground">Type</p>
              <p class="font-medium">{{ getOperationTitle(selectedOperation.type) }}</p>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Statut</p>
              <span class="badge" :class="getStatusBadgeClass(selectedOperation.status)">
                {{ getStatusText(selectedOperation.status) }}
              </span>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Démarré</p>
              <p class="text-sm">{{ formatDate(selectedOperation.started_at) }}</p>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Terminé</p>
              <p class="text-sm">
                {{ selectedOperation.completed_at 
                  ? formatDate(selectedOperation.completed_at) 
                  : 'En cours...' }}
              </p>
            </div>
          </div>
          
          <hr class="border-gray-200" />
          
          <div>
            <p class="text-sm font-medium text-gray-500 mb-2">Message</p>
            <p class="text-sm">{{ selectedOperation.message }}</p>
          </div>
          
          <div v-if="selectedOperation.result">
            <p class="text-sm font-medium text-gray-500 mb-2">Résultat</p>
            <pre class="p-3 bg-gray-100 rounded-md text-xs overflow-x-auto">{{ JSON.stringify(selectedOperation.result, null, 2) }}</pre>
          </div>
          
          <div v-if="selectedOperation.error">
            <p class="text-sm font-medium text-gray-500 mb-2">Erreur</p>
            <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div class="flex items-start">
                <AlertCircle :size="16" class="mr-2 text-red-600 mt-0.5" />
                <p class="text-sm text-red-700">{{ selectedOperation.error }}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div class="flex justify-end mt-6">
          <button class="btn btn-outline" @click="showDetailsDialog = false">
            Fermer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
// Toast functionality will be implemented locally
import { api } from '@/services/api'
import {
  PlayCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Ban,
  Search,
  ChevronRight,
  ChevronLeft,
  History,
  AlertCircle,
  FolderPlus,
  FolderMinus,
  Package,
  Download,
  Trash2,
  HardDrive,
  Wrench,
  Sparkles
} from 'lucide-vue-next'
// Using custom CSS classes from style.css

// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  // For now, using console.log - can be replaced with a proper notification system
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}

// State
const operations = ref<any[]>([])
const isLoading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('all')
const typeFilter = ref('all')
const currentPage = ref(1)
const itemsPerPage = 20

// Dialog state
const showDetailsDialog = ref(false)
const selectedOperation = ref<any>(null)

// Auto-refresh
let refreshInterval: any = null

// Computed
const activeOperations = computed(() => {
  return operations.value.filter(op => 
    op.status === 'pending' || op.status === 'running'
  )
})

const runningCount = computed(() => {
  return operations.value.filter(op => op.status === 'running').length
})

const completedCount = computed(() => {
  return operations.value.filter(op => op.status === 'completed').length
})

const failedCount = computed(() => {
  return operations.value.filter(op => op.status === 'failed').length
})

const filteredOperations = computed(() => {
  let filtered = operations.value

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(op =>
      op.type.toLowerCase().includes(query) ||
      op.message.toLowerCase().includes(query)
    )
  }

  // Filter by status
  if (statusFilter.value !== 'all') {
    filtered = filtered.filter(op => op.status === statusFilter.value)
  }

  // Filter by type
  if (typeFilter.value !== 'all') {
    filtered = filtered.filter(op => op.type === typeFilter.value)
  }

  return filtered
})

const totalPages = computed(() => {
  return Math.ceil(filteredOperations.value.length / itemsPerPage)
})

const paginatedOperations = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return filteredOperations.value.slice(start, end)
})

// Icons mapping
const operationIcons: Record<string, any> = {
  'environment_create': FolderPlus,
  'environment_delete': FolderMinus,
  'package_install': Package,
  'package_uninstall': Trash2,
  'package_update': Download,
  'cache_clean': HardDrive,
  'cache_export': Download,
  'cache_import': Download,
  'system_doctor': Wrench,
  'system_cleanup': Sparkles
}

// Methods
const getOperationIcon = (type: string) => {
  return operationIcons[type] || PlayCircle
}

const getOperationTitle = (type: string) => {
  const titles: Record<string, string> = {
    'environment_create': 'Création d\'environnement',
    'environment_delete': 'Suppression d\'environnement',
    'package_install': 'Installation de package',
    'package_uninstall': 'Désinstallation de package',
    'package_update': 'Mise à jour de package',
    'cache_clean': 'Nettoyage du cache',
    'cache_export': 'Export du cache',
    'cache_import': 'Import du cache',
    'system_doctor': 'Diagnostic système',
    'system_cleanup': 'Nettoyage système'
  }
  return titles[type] || type
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'pending': 'En attente',
    'running': 'En cours',
    'completed': 'Terminé',
    'failed': 'Échoué',
    'cancelled': 'Annulé'
  }
  return texts[status] || status
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'pending': return 'badge-gray'
    case 'running': return 'badge-primary'
    case 'completed': return 'badge-success'
    case 'failed': return 'badge-danger'
    case 'cancelled': return 'badge-gray'
    default: return 'badge-gray'
  }
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatRelativeTime = (date: string) => {
  const now = new Date()
  const past = new Date(date)
  const diffMs = now.getTime() - past.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'à l\'instant'
  if (diffMins < 60) return `il y a ${diffMins} min`
  if (diffMins < 1440) return `il y a ${Math.floor(diffMins / 60)} h`
  return `il y a ${Math.floor(diffMins / 1440)} j`
}

const formatDuration = (start: string, end: string) => {
  const startDate = new Date(start)
  const endDate = new Date(end)
  const diffMs = endDate.getTime() - startDate.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  
  if (diffSecs < 60) return `${diffSecs}s`
  if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ${diffSecs % 60}s`
  return `${Math.floor(diffSecs / 3600)}h ${Math.floor((diffSecs % 3600) / 60)}m`
}

const loadOperations = async () => {
  isLoading.value = true
  
  try {
    operations.value = await api.getOperations()
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Impossible de charger les opérations',
      variant: 'destructive'
    })
  } finally {
    isLoading.value = false
  }
}

const refreshOperations = async () => {
  await loadOperations()
  showToast({
    title: 'Actualisé',
    description: 'Liste des opérations mise à jour'
  })
}

const cancelOperation = async (operationId: string) => {
  try {
    await api.cancelOperation(operationId)
    await loadOperations()
    
    showToast({
      title: 'Succès',
      description: 'Opération annulée'
    })
  } catch (error) {
    showToast({
      title: 'Erreur',
      description: 'Impossible d\'annuler l\'opération',
      variant: 'destructive'
    })
  }
}

const viewOperationDetails = async (operation: any) => {
  try {
    selectedOperation.value = await api.getOperation(operation.id)
    showDetailsDialog.value = true
  } catch (error) {
    selectedOperation.value = operation
    showDetailsDialog.value = true
  }
}

// Auto-refresh active operations
const startAutoRefresh = () => {
  refreshInterval = setInterval(() => {
    if (activeOperations.value.length > 0) {
      loadOperations()
    }
  }, 5000) // Refresh every 5 seconds
}

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

// Reset pagination when filters change
watch([searchQuery, statusFilter, typeFilter], () => {
  currentPage.value = 1
})

// Lifecycle
onMounted(() => {
  loadOperations()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>