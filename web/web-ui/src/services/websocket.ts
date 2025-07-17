import type { WSMessage, WSMessageType } from '@/types'

type EventCallback = (data: any) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private listeners: Map<string, EventCallback[]> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false

  constructor() {
    this.connect()
  }

  connect(): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.isConnecting = true
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = (event) => {
        console.log('WebSocket connected:', event)
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.emit('connected', { timestamp: new Date().toISOString() })
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event)
        this.isConnecting = false
        this.ws = null
        this.emit('disconnected', { 
          code: event.code, 
          reason: event.reason,
          timestamp: new Date().toISOString()
        })
        this.attemptReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        this.emit('error', { error, timestamp: new Date().toISOString() })
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.isConnecting = false
      this.attemptReconnect()
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      this.emit('max_reconnect_attempts', { attempts: this.reconnectAttempts })
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connect()
    }, delay)
  }

  private handleMessage(message: WSMessage): void {
    console.log('WebSocket message received:', message)
    this.emit(message.type, message.data)
  }

  private emit(event: string, data: any): void {
    const callbacks = this.listeners.get(event) || []
    callbacks.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error(`Error in WebSocket callback for event '${event}':`, error)
      }
    })
  }

  // Public API
  subscribe(event: WSMessageType | string, callback: EventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)

    // Retourner une fonction de désabonnement
    return () => {
      const callbacks = this.listeners.get(event)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
      }
    }
  }

  unsubscribe(event: WSMessageType | string, callback?: EventCallback): void {
    if (!callback) {
      // Supprimer tous les callbacks pour cet événement
      this.listeners.delete(event)
      return
    }

    const callbacks = this.listeners.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message)
    }
  }

  getConnectionState(): string {
    if (!this.ws) return 'CLOSED'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING'
      case WebSocket.OPEN:
        return 'OPEN'
      case WebSocket.CLOSING:
        return 'CLOSING'
      case WebSocket.CLOSED:
        return 'CLOSED'
      default:
        return 'UNKNOWN'
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  // Méthodes spécialisées pour les événements GestVenv
  onEnvironmentCreated(callback: (data: { environment_name: string; environment: any }) => void) {
    return this.subscribe('environment_created', callback)
  }

  onEnvironmentDeleted(callback: (data: { environment_name: string }) => void) {
    return this.subscribe('environment_deleted', callback)
  }

  onEnvironmentUpdated(callback: (data: { environment_name: string; environment: any }) => void) {
    return this.subscribe('environment_updated', callback)
  }

  onPackageInstalled(callback: (data: { environment_name: string; package_name: string; package: any }) => void) {
    return this.subscribe('package_installed', callback)
  }

  onPackageUninstalled(callback: (data: { environment_name: string; package_name: string }) => void) {
    return this.subscribe('package_uninstalled', callback)
  }

  onOperationProgress(callback: (data: { operation_id: string; progress: number; message: string }) => void) {
    return this.subscribe('operation_progress', callback)
  }

  onOperationCompleted(callback: (data: { operation_id: string; result: any }) => void) {
    return this.subscribe('operation_completed', callback)
  }

  onCacheUpdated(callback: (data: any) => void) {
    return this.subscribe('cache_updated', callback)
  }

  onConnected(callback: (data: any) => void) {
    return this.subscribe('connected', callback)
  }

  onDisconnected(callback: (data: any) => void) {
    return this.subscribe('disconnected', callback)
  }

  onError(callback: (data: any) => void) {
    return this.subscribe('error', callback)
  }
}

// Instance exportée
export const websocket = new WebSocketService()
export default websocket