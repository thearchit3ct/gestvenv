import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Package, PackageInstall } from '@/types'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

export const usePackagesStore = defineStore('packages', () => {
  // State
  const packages = ref<Package[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // Current environment for packages
  const currentEnvironment = ref<string | null>(null)
  const currentGroup = ref<string | null>(null)

  // Computed
  const packagesByGroup = computed(() => {
    const groups: Record<string, Package[]> = {}
    
    packages.value.forEach(pkg => {
      if (!groups[pkg.group]) {
        groups[pkg.group] = []
      }
      groups[pkg.group].push(pkg)
    })
    
    return groups
  })

  const outdatedPackages = computed(() => 
    packages.value.filter(pkg => pkg.status === 'outdated')
  )

  const totalPackages = computed(() => packages.value.length)
  const totalSize = computed(() => 
    packages.value.reduce((sum, pkg) => sum + pkg.size_mb, 0)
  )

  // Actions
  async function fetchPackages(envName: string, group?: string, outdatedOnly = false) {
    loading.value = true
    error.value = null
    currentEnvironment.value = envName
    currentGroup.value = group || null
    
    try {
      packages.value = await api.getEnvironmentPackages(envName, { 
        group, 
        outdated_only: outdatedOnly 
      })
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du chargement des packages'
      console.error('Failed to fetch packages:', err)
    } finally {
      loading.value = false
    }
  }

  async function installPackage(envName: string, packageData: PackageInstall) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.installPackage(envName, packageData)
      
      if (response.success) {
        // Le package sera ajouté via WebSocket
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de l\'installation'
      console.error('Failed to install package:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function uninstallPackage(envName: string, packageName: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.uninstallPackage(envName, packageName)
      
      if (response.success) {
        // Le package sera supprimé via WebSocket
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de la désinstallation'
      console.error('Failed to uninstall package:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updatePackages(envName: string, packageNames?: string[]) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.updatePackages(envName, packageNames)
      
      if (response.success) {
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de la mise à jour'
      console.error('Failed to update packages:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearPackages() {
    packages.value = []
    currentEnvironment.value = null
    currentGroup.value = null
  }

  // WebSocket event handlers
  function setupWebSocketListeners() {
    websocket.onPackageInstalled((data) => {
      console.log('Package installed:', data)
      
      // Refresh packages if it's for the current environment
      if (currentEnvironment.value === data.environment_name) {
        fetchPackages(
          data.environment_name, 
          currentGroup.value || undefined
        )
      }
    })

    websocket.onPackageUninstalled((data) => {
      console.log('Package uninstalled:', data)
      
      // Remove package from local state
      if (currentEnvironment.value === data.environment_name) {
        packages.value = packages.value.filter(
          pkg => pkg.name !== data.package_name
        )
      }
    })
  }

  // Helper functions
  function getPackageByName(name: string) {
    return packages.value.find(pkg => pkg.name === name)
  }

  function getPackagesByGroup(group: string) {
    return packages.value.filter(pkg => pkg.group === group)
  }

  function getAvailableGroups() {
    const groups = new Set(packages.value.map(pkg => pkg.group))
    return Array.from(groups).sort()
  }

  // Initialize
  function initialize() {
    setupWebSocketListeners()
  }

  return {
    // State
    packages,
    loading,
    error,
    currentEnvironment,
    currentGroup,
    
    // Computed
    packagesByGroup,
    outdatedPackages,
    totalPackages,
    totalSize,
    
    // Actions
    fetchPackages,
    installPackage,
    uninstallPackage,
    updatePackages,
    clearError,
    clearPackages,
    
    // Helpers
    getPackageByName,
    getPackagesByGroup,
    getAvailableGroups,
    initialize
  }
})