<template>
  <div class="container mx-auto p-6">
    <!-- Header Section -->
    <div class="mb-6">
      <button
        class="btn btn-ghost btn-sm mb-4"
        @click="$router.push('/environments')"
      >
        <ArrowLeft :size="16" class="mr-2" />
        Retour aux environnements
      </button>
      
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <h1 class="text-3xl font-bold">{{ environment?.name || 'Chargement...' }}</h1>
          <span
            class="badge"
            :class="environment?.status === 'healthy' ? 'badge-success' : 
                     environment?.status === 'warning' ? 'badge-warning' : 'badge-danger'"
          >
            {{ statusText }}
          </span>
          <span v-if="environment?.active" class="badge badge-primary">Actif</span>
        </div>
        
        <div class="flex items-center space-x-2">
          <button
            class="btn btn-outline btn-sm"
            @click="refreshEnvironment"
            :disabled="isLoading"
          >
            <RefreshCw :size="16" :class="{ 'animate-spin': isLoading }" />
          </button>
          <button
            v-if="!environment?.active"
            class="btn btn-outline btn-sm"
            @click="activateEnvironment"
            :disabled="isActivating"
          >
            <Power :size="16" class="mr-2" />
            Activer
          </button>
          <button
            class="btn btn-outline btn-sm"
            @click="syncEnvironment"
            :disabled="isSyncing"
          >
            <RefreshCw :size="16" class="mr-2" :class="{ 'animate-spin': isSyncing }" />
            Synchroniser
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !environment" class="space-y-4">
      <div class="card">
        <div class="card-body p-6">
          <div class="space-y-3">
            <div class="h-4 w-1/3 bg-gray-200 rounded animate-pulse" />
            <div class="h-4 w-1/2 bg-gray-200 rounded animate-pulse" />
            <div class="h-4 w-2/3 bg-gray-200 rounded animate-pulse" />
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div v-else-if="environment" class="space-y-6">
      <!-- Info Cards -->
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div class="card">
          <div class="card-header pb-3">
            <h3 class="text-sm font-medium text-gray-500">
              Version Python
            </h3>
          </div>
          <div class="card-body">
            <div class="text-2xl font-bold">{{ environment.python_version || 'N/A' }}</div>
          </div>
        </div>
        
        <div class="card">
          <div class="card-header pb-3">
            <h3 class="text-sm font-medium text-gray-500">
              Backend
            </h3>
          </div>
          <div class="card-body">
            <div class="text-2xl font-bold">{{ environment.backend }}</div>
          </div>
        </div>
        
        <div class="card">
          <div class="card-header pb-3">
            <h3 class="text-sm font-medium text-gray-500">
              Packages
            </h3>
          </div>
          <div class="card-body">
            <div class="text-2xl font-bold">{{ environment.package_count || 0 }}</div>
          </div>
        </div>
        
        <div class="card">
          <div class="card-header pb-3">
            <h3 class="text-sm font-medium text-gray-500">
              Taille
            </h3>
          </div>
          <div class="card-body">
            <div class="text-2xl font-bold">{{ formatSize(environment.size_mb) }}</div>
          </div>
        </div>
      </div>

      <!-- Environment Details -->
      <div class="card">
        <div class="card-header">
          <h2 class="text-xl font-semibold">Détails de l'environnement</h2>
        </div>
        <div class="card-body">
          <div class="space-y-4">
            <div class="grid gap-4 md:grid-cols-2">
              <div>
                <p class="text-sm font-medium text-gray-500">Chemin</p>
                <p class="text-sm font-mono">{{ environment.path }}</p>
              </div>
              <div>
                <p class="text-sm font-medium text-gray-500">Créé le</p>
                <p class="text-sm">{{ formatDate(environment.created_at) }}</p>
              </div>
              <div>
                <p class="text-sm font-medium text-gray-500">Dernière utilisation</p>
                <p class="text-sm">{{ environment.last_used ? formatDate(environment.last_used) : 'Jamais' }}</p>
              </div>
              <div>
                <p class="text-sm font-medium text-gray-500">Statut</p>
                <div class="flex items-center space-x-2">
                  <div
                    class="h-2 w-2 rounded-full"
                    :class="{
                      'bg-green-500': environment.status === 'healthy',
                      'bg-yellow-500': environment.status === 'warning',
                      'bg-red-500': environment.status === 'error'
                    }"
                  />
                  <span class="text-sm">{{ statusText }}</span>
                </div>
              </div>
            </div>
            
            <!-- Health Info -->
            <div v-if="environment.health_info && Object.keys(environment.health_info).length > 0">
              <hr class="border-gray-200 my-4" />
              <div>
                <p class="text-sm font-medium text-gray-500 mb-2">Informations de santé</p>
                <div class="space-y-2">
                  <div v-for="(value, key) in environment.health_info" :key="key" class="flex justify-between text-sm">
                    <span class="text-gray-500">{{ key }}</span>
                    <span class="font-mono">{{ value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Packages Section -->
      <div class="card">
        <div class="card-header">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-semibold">Packages installés</h2>
            <div class="flex items-center space-x-2">
              <div class="relative">
                <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="searchQuery"
                  placeholder="Rechercher un package..."
                  class="pl-9 w-64"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                @click="showInstallDialog = true"
              >
                <Plus :size="16" class="mr-2" />
                Installer
              </button>
              <Button
                v-if="hasOutdatedPackages"
                variant="outline"
                size="sm"
                @click="updateAllPackages"
                :disabled="isUpdating"
              >
                <Download :size="16" class="mr-2" />
                Tout mettre à jour
              </button>
              <div v-if="selectedPackages.length > 0" class="relative">
                <button class="btn btn-outline btn-sm" @click="showDropdown = !showDropdown">
                  Actions ({{ selectedPackages.length }})
                  <ChevronDown :size="16" class="ml-2" />
                </button>
                <div v-if="showDropdown" class="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                  <button @click="bulkUninstall(); showDropdown = false" class="w-full px-4 py-2 text-left hover:bg-gray-100 flex items-center">
                    <Trash2 :size="16" class="mr-2" />
                    Désinstaller la sélection
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="card-body">
          <!-- Package List -->
          <div v-if="filteredPackages.length > 0" class="border rounded-lg">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b bg-gray-50">
                    <th class="p-3 text-left">
                      <input
                        type="checkbox"
                        v-model="selectAll"
                        @change="toggleSelectAll"
                      />
                    </th>
                    <th class="p-3 text-left text-sm font-medium">Package</th>
                    <th class="p-3 text-left text-sm font-medium">Version installée</th>
                    <th class="p-3 text-left text-sm font-medium">Dernière version</th>
                    <th class="p-3 text-left text-sm font-medium">Statut</th>
                    <th class="p-3 text-left text-sm font-medium">Groupe</th>
                    <th class="p-3 text-left text-sm font-medium">Taille</th>
                    <th class="p-3 text-right text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="pkg in filteredPackages"
                    :key="pkg.name"
                    class="border-b transition-colors hover:bg-gray-50"
                  >
                    <td class="p-3">
                      <input
                        type="checkbox"
                        v-model="selectedPackages"
                        :value="pkg.name"
                      />
                    </td>
                    <td class="p-3">
                      <div>
                        <p class="font-medium">{{ pkg.name }}</p>
                        <p v-if="pkg.description" class="text-sm text-gray-500">
                          {{ pkg.description }}
                        </p>
                      </div>
                    </td>
                    <td class="p-3 font-mono text-sm">
                      {{ pkg.installed_version || 'N/A' }}
                    </td>
                    <td class="p-3 font-mono text-sm">
                      {{ pkg.latest_version || 'N/A' }}
                    </td>
                    <td class="p-3">
                      <span
                        class="badge"
                        :class="pkg.status === 'installed' ? 'badge-success' : 
                                 pkg.status === 'outdated' ? 'badge-warning' : 'badge-danger'"
                      >
                        {{ packageStatusText(pkg.status) }}
                      </span>
                    </td>
                    <td class="p-3 text-sm">{{ pkg.group }}</td>
                    <td class="p-3 text-sm">{{ formatSize(pkg.size_mb) }}</td>
                    <td class="p-3 text-right">
                      <div class="flex items-center justify-end space-x-2">
                        <button
                          v-if="pkg.status === 'outdated'"
                          class="btn btn-ghost btn-sm"
                          @click="updatePackage(pkg.name)"
                          :disabled="isUpdating"
                          title="Mettre à jour"
                        >
                          <Download :size="16" />
                        </button>
                        <button
                          class="btn btn-ghost btn-sm"
                          @click="uninstallPackage(pkg.name)"
                          title="Désinstaller"
                        >
                          <Trash2 :size="16" />
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <!-- Empty State -->
          <div v-else class="text-center py-12">
            <Package :size="48" class="mx-auto text-gray-400 mb-4" />
            <p class="text-gray-500">
              {{ searchQuery ? 'Aucun package trouvé' : 'Aucun package installé' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
      <div class="flex items-start">
        <AlertCircle :size="16" class="mr-2 text-red-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-red-900">Erreur</h4>
          <p class="text-sm text-red-700 mt-1">{{ error }}</p>
        </div>
      </div>
    </div>

    <!-- Success Message -->
    <div v-if="successMessage" class="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
      <div class="flex items-start">
        <CheckCircle2 :size="16" class="mr-2 text-green-600 mt-0.5" />
        <div>
          <h4 class="text-sm font-medium text-green-900">Succès</h4>
          <p class="text-sm text-green-700 mt-1">{{ successMessage }}</p>
        </div>
      </div>
    </div>

    <!-- Install Package Dialog -->
    <div v-if="showInstallDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="mb-4">
          <h3 class="text-lg font-semibold">Installer un package</h3>
          <p class="text-sm text-gray-500 mt-1">
            Entrez le nom du package à installer dans cet environnement.
          </p>
        </div>
        
        <div class="space-y-4">
          <div>
            <label for="package-name" class="form-label">Nom du package</label>
            <input
              id="package-name"
              v-model="newPackageName"
              placeholder="ex: requests, numpy==1.21.0"
              @keydown.enter="installPackage"
              class="form-input"
            />
          </div>
          
          <div class="flex items-center space-x-2">
            <input type="checkbox" id="editable" v-model="installEditable" class="mr-2" />
            <label for="editable" class="form-label">Installation éditable (-e)</label>
          </div>
          
          <div class="flex items-center space-x-2">
            <input type="checkbox" id="upgrade" v-model="installUpgrade" class="mr-2" />
            <label for="upgrade" class="form-label">Mettre à jour si déjà installé</label>
          </div>
        </div>
        
        <div class="flex justify-end space-x-2 mt-6">
          <button class="btn btn-outline" @click="showInstallDialog = false">
            Annuler
          </button>
          <button
            class="btn btn-primary"
            @click="installPackage"
            :disabled="!newPackageName.trim() || isInstalling"
          >
            <Loader2 v-if="isInstalling" :size="16" class="mr-2 animate-spin" />
            Installer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEnvironmentsStore } from '@/stores/environments'
import { usePackagesStore } from '@/stores/packages'
// Toast functionality will be implemented locally
import {
  ArrowLeft,
  RefreshCw,
  Power,
  Plus,
  Search,
  Download,
  Trash2,
  ChevronDown,
  Package,
  AlertCircle,
  CheckCircle2,
  Loader2
} from 'lucide-vue-next'
// Using custom CSS classes from style.css
import type { EnvironmentDetails, Package as PackageType } from '@/types'

// Props & State
const route = useRoute()
const router = useRouter()
// Simple toast notification function
const showToast = (options: { title: string; description?: string; variant?: string }) => {
  // For now, using console.log - can be replaced with a proper notification system
  console.log(`[${options.variant || 'info'}] ${options.title}: ${options.description || ''}`)
}
const environmentsStore = useEnvironmentsStore()
const packagesStore = usePackagesStore()

const environment = ref<EnvironmentDetails | null>(null)
const isLoading = ref(false)
const isActivating = ref(false)
const isSyncing = ref(false)
const isInstalling = ref(false)
const isUpdating = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Package Management
const searchQuery = ref('')
const selectedPackages = ref<string[]>([])
const showInstallDialog = ref(false)
const newPackageName = ref('')
const installEditable = ref(false)
const installUpgrade = ref(false)
const showDropdown = ref(false)

// Computed
const envName = computed(() => route.params.name as string)

const statusText = computed(() => {
  const status = environment.value?.status
  switch (status) {
    case 'healthy': return 'Sain'
    case 'warning': return 'Avertissement'
    case 'error': return 'Erreur'
    default: return 'Inconnu'
  }
})

const filteredPackages = computed(() => {
  if (!environment.value?.packages) return []
  if (!searchQuery.value) return environment.value.packages
  
  const query = searchQuery.value.toLowerCase()
  return environment.value.packages.filter(pkg =>
    pkg.name.toLowerCase().includes(query) ||
    pkg.description?.toLowerCase().includes(query)
  )
})

const hasOutdatedPackages = computed(() => {
  return environment.value?.packages?.some(pkg => pkg.status === 'outdated') ?? false
})

const selectAll = computed({
  get: () => {
    if (filteredPackages.value.length === 0) return false
    return filteredPackages.value.every(pkg => selectedPackages.value.includes(pkg.name))
  },
  set: (value: boolean) => {
    if (value) {
      selectedPackages.value = filteredPackages.value.map(pkg => pkg.name)
    } else {
      selectedPackages.value = []
    }
  }
})

// Methods
const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatSize = (mb: number) => {
  if (mb < 1) return `${(mb * 1024).toFixed(1)} KB`
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

const packageStatusText = (status: string) => {
  switch (status) {
    case 'installed': return 'Installé'
    case 'outdated': return 'Obsolète'
    case 'missing': return 'Manquant'
    default: return status
  }
}

const toggleSelectAll = () => {
  // La valeur est déjà mise à jour par v-model
}

const loadEnvironment = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    environment.value = await environmentsStore.fetchEnvironmentDetails(envName.value)
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

const refreshEnvironment = async () => {
  await loadEnvironment()
  successMessage.value = 'Environnement actualisé'
  setTimeout(() => { successMessage.value = null }, 3000)
}

const activateEnvironment = async () => {
  isActivating.value = true
  error.value = null
  
  try {
    await environmentsStore.activateEnvironment(envName.value)
    await loadEnvironment()
    showToast({
      title: 'Succès',
      description: 'Environnement activé'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de l\'activation'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isActivating.value = false
  }
}

const syncEnvironment = async () => {
  isSyncing.value = true
  error.value = null
  
  try {
    await environmentsStore.syncEnvironment(envName.value)
    await loadEnvironment()
    showToast({
      title: 'Succès',
      description: 'Environnement synchronisé'
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la synchronisation'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isSyncing.value = false
  }
}

const installPackage = async () => {
  if (!newPackageName.value.trim()) return
  
  isInstalling.value = true
  error.value = null
  
  try {
    await packagesStore.installPackage(envName.value, {
      name: newPackageName.value,
      editable: installEditable.value,
      upgrade: installUpgrade.value
    })
    
    showInstallDialog.value = false
    newPackageName.value = ''
    installEditable.value = false
    installUpgrade.value = false
    
    await loadEnvironment()
    
    showToast({
      title: 'Succès',
      description: `Package ${newPackageName.value} installé`
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de l\'installation'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isInstalling.value = false
  }
}

const uninstallPackage = async (packageName: string) => {
  error.value = null
  
  try {
    await packagesStore.uninstallPackage(envName.value, packageName)
    await loadEnvironment()
    
    showToast({
      title: 'Succès',
      description: `Package ${packageName} désinstallé`
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la désinstallation'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  }
}

const updatePackage = async (packageName: string) => {
  isUpdating.value = true
  error.value = null
  
  try {
    await packagesStore.updatePackages(envName.value, [packageName])
    await loadEnvironment()
    
    showToast({
      title: 'Succès',
      description: `Package ${packageName} mis à jour`
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la mise à jour'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isUpdating.value = false
  }
}

const updateAllPackages = async () => {
  const outdatedPackages = environment.value?.packages
    ?.filter(pkg => pkg.status === 'outdated')
    .map(pkg => pkg.name) ?? []
  
  if (outdatedPackages.length === 0) return
  
  isUpdating.value = true
  error.value = null
  
  try {
    await packagesStore.updatePackages(envName.value, outdatedPackages)
    await loadEnvironment()
    
    showToast({
      title: 'Succès',
      description: `${outdatedPackages.length} packages mis à jour`
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la mise à jour'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  } finally {
    isUpdating.value = false
  }
}

const bulkUninstall = async () => {
  if (selectedPackages.value.length === 0) return
  
  error.value = null
  
  try {
    for (const packageName of selectedPackages.value) {
      await packagesStore.uninstallPackage(envName.value, packageName)
    }
    
    selectedPackages.value = []
    await loadEnvironment()
    
    showToast({
      title: 'Succès',
      description: `${selectedPackages.value.length} packages désinstallés`
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la désinstallation'
    showToast({
      title: 'Erreur',
      description: error.value,
      variant: 'destructive'
    })
  }
}

// Lifecycle
onMounted(() => {
  loadEnvironment()
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