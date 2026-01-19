import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  Environment, 
  EnvironmentDetails, 
  EnvironmentCreate, 
  EnvironmentFilters, 
  EnvironmentSort,
  Package 
} from '@/types'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

export const useEnvironmentsStore = defineStore('environments', () => {
  // State
  const environments = ref<Environment[]>([])
  const currentEnvironment = ref<EnvironmentDetails | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // Filters and sorting
  const filters = ref<EnvironmentFilters>({})
  const sort = ref<EnvironmentSort>({ field: 'name', direction: 'asc' })

  // Computed
  const filteredEnvironments = computed(() => {
    let result = [...environments.value]

    // Apply filters
    if (filters.value.backend) {
      result = result.filter(env => env.backend === filters.value.backend)
    }
    
    if (filters.value.status) {
      result = result.filter(env => env.status === filters.value.status)
    }
    
    if (filters.value.search) {
      const search = filters.value.search.toLowerCase()
      result = result.filter(env => 
        env.name.toLowerCase().includes(search) ||
        env.path.toLowerCase().includes(search)
      )
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal: any, bVal: any
      
      switch (sort.value.field) {
        case 'created':
          aVal = new Date(a.created_at).getTime()
          bVal = new Date(b.created_at).getTime()
          break
        case 'used':
          aVal = a.last_used ? new Date(a.last_used).getTime() : 0
          bVal = b.last_used ? new Date(b.last_used).getTime() : 0
          break
        case 'size':
          aVal = a.size_mb
          bVal = b.size_mb
          break
        default: // name
          aVal = a.name.toLowerCase()
          bVal = b.name.toLowerCase()
      }

      if (sort.value.direction === 'desc') {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
      } else {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      }
    })

    return result
  })

  const totalEnvironments = computed(() => environments.value.length)
  const activeEnvironment = computed(() => 
    environments.value.find(env => env.active)
  )

  // Actions
  async function fetchEnvironments() {
    loading.value = true
    error.value = null
    
    try {
      const params: any = {}
      if (filters.value.backend) params.backend = filters.value.backend
      if (filters.value.status) params.status = filters.value.status
      params.sort_by = sort.value.field

      environments.value = await api.getEnvironments(params)
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du chargement des environnements'
      console.error('Failed to fetch environments:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchEnvironmentDetails(name: string) {
    loading.value = true
    error.value = null

    try {
      currentEnvironment.value = await api.getEnvironment(name)
      return currentEnvironment.value
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du chargement des détails'
      console.error('Failed to fetch environment details:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  async function createEnvironment(data: EnvironmentCreate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.createEnvironment(data)
      
      if (response.success) {
        // L'environnement sera ajouté via WebSocket
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de la création'
      console.error('Failed to create environment:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteEnvironment(name: string, force = false) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.deleteEnvironment(name, force)
      
      if (response.success) {
        // L'environnement sera supprimé via WebSocket
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de la suppression'
      console.error('Failed to delete environment:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function activateEnvironment(name: string) {
    try {
      const response = await api.activateEnvironment(name)
      
      if (response.success) {
        // Mettre à jour l'état local
        environments.value.forEach(env => {
          env.active = env.name === name
        })
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de l\'activation'
      console.error('Failed to activate environment:', err)
      throw err
    }
  }

  async function syncEnvironment(name: string, groups?: string, clean = false) {
    try {
      const response = await api.syncEnvironment(name, { groups, clean })
      
      if (response.success) {
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de la synchronisation'
      console.error('Failed to sync environment:', err)
      throw err
    }
  }

  // Environment packages
  async function fetchEnvironmentPackages(name: string, group?: string, outdatedOnly = false) {
    try {
      return await api.getEnvironmentPackages(name, { 
        group, 
        outdated_only: outdatedOnly 
      })
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du chargement des packages'
      console.error('Failed to fetch packages:', err)
      throw err
    }
  }

  // Filters and sorting
  function setFilters(newFilters: Partial<EnvironmentFilters>) {
    filters.value = { ...filters.value, ...newFilters }
  }

  function setSort(newSort: Partial<EnvironmentSort>) {
    sort.value = { ...sort.value, ...newSort }
  }

  function clearFilters() {
    filters.value = {}
  }

  function clearError() {
    error.value = null
  }

  // WebSocket event handlers
  function setupWebSocketListeners() {
    websocket.onEnvironmentCreated((data) => {
      console.log('Environment created:', data)
      fetchEnvironments() // Refresh list
    })

    websocket.onEnvironmentDeleted((data) => {
      console.log('Environment deleted:', data)
      environments.value = environments.value.filter(
        env => env.name !== data.environment_name
      )
      
      // Clear current environment if it was deleted
      if (currentEnvironment.value?.name === data.environment_name) {
        currentEnvironment.value = null
      }
    })

    websocket.onEnvironmentUpdated((data) => {
      console.log('Environment updated:', data)
      const index = environments.value.findIndex(
        env => env.name === data.environment_name
      )
      
      if (index !== -1) {
        environments.value[index] = { ...environments.value[index], ...data.environment }
      }
    })
  }

  // Helper functions
  function getEnvironmentByName(name: string) {
    return environments.value.find(env => env.name === name)
  }

  function getEnvironmentStatus(name: string) {
    const env = getEnvironmentByName(name)
    return env?.status
  }

  // Initialize
  function initialize() {
    setupWebSocketListeners()
    fetchEnvironments()
  }

  return {
    // State
    environments,
    currentEnvironment,
    loading,
    error,
    filters,
    sort,
    
    // Computed
    filteredEnvironments,
    totalEnvironments,
    activeEnvironment,
    
    // Actions
    fetchEnvironments,
    fetchEnvironmentDetails,
    createEnvironment,
    deleteEnvironment,
    activateEnvironment,
    syncEnvironment,
    fetchEnvironmentPackages,
    
    // Filters
    setFilters,
    setSort,
    clearFilters,
    clearError,
    
    // Helpers
    getEnvironmentByName,
    getEnvironmentStatus,
    initialize
  }
})