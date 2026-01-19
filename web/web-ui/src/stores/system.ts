import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SystemInfo, Operation, CacheInfo } from '@/types'
import { OperationStatus } from '@/types'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

export const useSystemStore = defineStore('system', () => {
  // State
  const systemInfo = ref<SystemInfo | null>(null)
  const cacheInfo = ref<CacheInfo | null>(null)
  const operations = ref<Operation[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // WebSocket connection state
  const wsConnected = ref(false)
  const wsReconnecting = ref(false)

  // Computed
  const runningOperations = computed(() => 
    operations.value.filter(op => op.status === 'running')
  )

  const recentOperations = computed(() => 
    operations.value
      .filter(op => op.status !== 'pending')
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
      .slice(0, 10)
  )

  const systemHealth = computed(() => {
    if (!systemInfo.value) return 'unknown'
    
    // Logique simple pour déterminer la santé
    const availableBackends = systemInfo.value.backends_available.length
    const diskUsage = systemInfo.value.disk_usage
    
    if (availableBackends === 0) return 'error'
    if (diskUsage.used / diskUsage.total > 0.9) return 'warning'
    
    return 'healthy'
  })

  // Actions
  async function fetchSystemInfo() {
    loading.value = true
    error.value = null
    
    try {
      systemInfo.value = await api.getSystemInfo()
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du chargement des informations système'
      console.error('Failed to fetch system info:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchCacheInfo() {
    try {
      cacheInfo.value = await api.getCacheInfo()
    } catch (err: any) {
      console.error('Failed to fetch cache info:', err)
    }
  }

  async function fetchOperations(operationType?: string) {
    try {
      operations.value = await api.getOperations(operationType)
    } catch (err: any) {
      console.error('Failed to fetch operations:', err)
    }
  }

  async function getOperation(operationId: string) {
    try {
      return await api.getOperation(operationId)
    } catch (err: any) {
      console.error('Failed to fetch operation:', err)
      throw err
    }
  }

  async function cancelOperation(operationId: string) {
    try {
      const response = await api.cancelOperation(operationId)
      
      if (response.success) {
        // Mettre à jour l'opération localement
        const index = operations.value.findIndex(op => op.id === operationId)
        if (index !== -1) {
          operations.value[index].status = OperationStatus.CANCELLED
        }
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de l\'annulation'
      console.error('Failed to cancel operation:', err)
      throw err
    }
  }

  async function runDoctor(envName?: string, autoFix = false) {
    try {
      const response = await api.runDoctor({ env_name: envName, auto_fix: autoFix })
      
      if (response.success) {
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du diagnostic'
      console.error('Failed to run doctor:', err)
      throw err
    }
  }

  async function cleanupSystem(orphanedOnly = false, cleanCache = false) {
    try {
      const response = await api.cleanupSystem({ 
        orphaned_only: orphanedOnly, 
        clean_cache: cleanCache 
      })
      
      if (response.success) {
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du nettoyage'
      console.error('Failed to cleanup system:', err)
      throw err
    }
  }

  async function cleanCache(olderThan?: number, sizeLimit?: string) {
    try {
      const response = await api.cleanCache({ 
        older_than: olderThan, 
        size_limit: sizeLimit 
      })
      
      if (response.success) {
        // Rafraîchir les informations du cache
        await fetchCacheInfo()
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors du nettoyage du cache'
      console.error('Failed to clean cache:', err)
      throw err
    }
  }

  async function exportCache(outputPath: string, compress = true) {
    try {
      const response = await api.exportCache(outputPath, compress)
      
      if (response.success) {
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de l\'export du cache'
      console.error('Failed to export cache:', err)
      throw err
    }
  }

  async function importCache(sourcePath: string, merge = false, verify = true) {
    try {
      const response = await api.importCache(sourcePath, merge, verify)
      
      if (response.success) {
        // Rafraîchir les informations du cache
        await fetchCacheInfo()
        return response
      } else {
        throw new Error(response.message)
      }
    } catch (err: any) {
      error.value = err.message || 'Erreur lors de l\'import du cache'
      console.error('Failed to import cache:', err)
      throw err
    }
  }

  function clearError() {
    error.value = null
  }

  // WebSocket event handlers
  function setupWebSocketListeners() {
    websocket.onConnected(() => {
      wsConnected.value = true
      wsReconnecting.value = false
      console.log('WebSocket connected')
    })

    websocket.onDisconnected(() => {
      wsConnected.value = false
      wsReconnecting.value = true
      console.log('WebSocket disconnected')
    })

    websocket.onError((data) => {
      console.error('WebSocket error:', data)
    })

    websocket.onOperationProgress((data) => {
      // Mettre à jour l'opération avec le nouveau progrès
      const index = operations.value.findIndex(op => op.id === data.operation_id)
      if (index !== -1) {
        operations.value[index].progress = data.progress
        operations.value[index].message = data.message
      }
    })

    websocket.onOperationCompleted((data) => {
      // Mettre à jour l'opération comme terminée
      const index = operations.value.findIndex(op => op.id === data.operation_id)
      if (index !== -1) {
        operations.value[index].status = OperationStatus.COMPLETED
        operations.value[index].progress = 100
        operations.value[index].result = data.result
        operations.value[index].completed_at = new Date().toISOString()
      }
    })

    websocket.onCacheUpdated((data) => {
      // Mettre à jour les informations du cache
      if (cacheInfo.value) {
        Object.assign(cacheInfo.value, data)
      }
    })
  }

  // Helper functions
  function getOperationById(id: string) {
    return operations.value.find(op => op.id === id)
  }

  function getOperationsByType(type: string) {
    return operations.value.filter(op => op.type === type)
  }

  function formatBytes(bytes: number) {
    if (bytes === 0) return '0 B'
    
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  function formatCacheSize() {
    if (!cacheInfo.value) return '0 MB'
    return formatBytes(cacheInfo.value.total_size_mb * 1024 * 1024)
  }

  // Auto-refresh
  function startAutoRefresh(interval = 30000) {
    setInterval(() => {
      if (wsConnected.value) {
        fetchOperations()
        fetchCacheInfo()
      }
    }, interval)
  }

  // Initialize
  async function initialize() {
    setupWebSocketListeners()
    await Promise.all([
      fetchSystemInfo(),
      fetchCacheInfo(),
      fetchOperations()
    ])
    startAutoRefresh()
  }

  return {
    // State
    systemInfo,
    cacheInfo,
    operations,
    loading,
    error,
    wsConnected,
    wsReconnecting,
    
    // Computed
    runningOperations,
    recentOperations,
    systemHealth,
    
    // Actions
    fetchSystemInfo,
    fetchCacheInfo,
    fetchOperations,
    getOperation,
    cancelOperation,
    runDoctor,
    cleanupSystem,
    cleanCache,
    exportCache,
    importCache,
    clearError,
    
    // Helpers
    getOperationById,
    getOperationsByType,
    formatBytes,
    formatCacheSize,
    initialize
  }
})